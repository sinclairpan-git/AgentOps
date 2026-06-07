"""PostgreSQL-backed runtime repository for AO57 production ingestion."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any

from agentops.storage.repository import (
    InMemoryRepository,
    _runtime_attempt_identity,
    _runtime_attempt_matches,
    _runtime_number_sort_value,
    utc_now,
)

MIGRATION_DIR = Path(__file__).resolve().parent / "migrations"
RUNTIME_OPERATIONS_MIGRATION = MIGRATION_DIR / "001_runtime_operations.sql"
_RUNTIME_CONNECTION: ContextVar[Any | None] = ContextVar(
    "agentops_runtime_connection",
    default=None,
)


def runtime_operations_schema_sql() -> str:
    return RUNTIME_OPERATIONS_MIGRATION.read_text(encoding="utf-8")


class PostgresRepository(InMemoryRepository):
    """Runtime-focused PostgreSQL adapter with in-memory fallback for other domains.

    Existing AgentOps surfaces still use the broad repository API. This adapter
    persists AO57 runtime facts and receipts to PostgreSQL while inheriting the
    non-runtime in-memory behavior until those domains receive their own storage
    migration.
    """

    def __init__(
        self,
        database_url: str,
        *,
        connect_timeout_seconds: int = 5,
        install_schema: bool = False,
    ) -> None:
        super().__init__()
        self.database_url = database_url
        self.connect_timeout_seconds = connect_timeout_seconds
        if install_schema:
            self.install_schema()

    def install_schema(self) -> None:
        statements = [
            statement.strip()
            for statement in runtime_operations_schema_sql().split(";")
            if statement.strip()
        ]
        with self._new_connection() as connection:
            with connection.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)

    @contextmanager
    def runtime_ingestion_transaction(self) -> Iterator[None]:
        existing = _RUNTIME_CONNECTION.get()
        if existing is not None:
            yield
            return
        with self._new_connection() as connection:
            token = _RUNTIME_CONNECTION.set(connection)
            try:
                yield
            finally:
                _RUNTIME_CONNECTION.reset(token)

    def runtime_idempotency_outcome(
        self, idempotency_key: str, payload_hash: str
    ) -> str:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT payload_hash
                    FROM agentops_runtime_idempotency
                    WHERE idempotency_key = %s
                    """,
                    (idempotency_key,),
                )
                row = cursor.fetchone()
        if row is None:
            return "new"
        stored_payload_hash = str(row[0])
        return "deduplicated" if stored_payload_hash == payload_hash else "conflict"

    def remember_runtime_idempotency(
        self, idempotency_key: str, event_id: str, payload_hash: str
    ) -> None:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO agentops_runtime_idempotency (
                      idempotency_key, event_id, payload_hash
                    )
                    VALUES (%s, %s, %s)
                    ON CONFLICT (idempotency_key) DO NOTHING
                    """,
                    (idempotency_key, event_id, payload_hash),
                )

    def write_runtime_outbox_receipt(self, receipt: dict[str, Any]) -> None:
        receipt_id = str(receipt.get("batch_id") or receipt.get("outbox_id"))
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO agentops_runtime_outbox_receipts (
                      receipt_id, batch_id, outbox_id, producer, replay_reason,
                      outbox_state, accepted_count, deduplicated_count, stale_count,
                      rejected_count, dlq_count, audit_id, record
                    )
                    VALUES (
                      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
                    )
                    ON CONFLICT (receipt_id) DO UPDATE SET
                      batch_id = EXCLUDED.batch_id,
                      outbox_id = EXCLUDED.outbox_id,
                      producer = EXCLUDED.producer,
                      replay_reason = EXCLUDED.replay_reason,
                      outbox_state = EXCLUDED.outbox_state,
                      accepted_count = EXCLUDED.accepted_count,
                      deduplicated_count = EXCLUDED.deduplicated_count,
                      stale_count = EXCLUDED.stale_count,
                      rejected_count = EXCLUDED.rejected_count,
                      dlq_count = EXCLUDED.dlq_count,
                      audit_id = EXCLUDED.audit_id,
                      received_at = now(),
                      record = EXCLUDED.record
                    """,
                    (
                        receipt_id,
                        str(receipt.get("batch_id") or ""),
                        str(receipt.get("outbox_id") or ""),
                        str(receipt.get("producer") or ""),
                        str(receipt.get("replay_reason") or ""),
                        str(receipt.get("outbox_state") or ""),
                        int(receipt.get("accepted_count") or 0),
                        int(receipt.get("deduplicated_count") or 0),
                        int(receipt.get("stale_count") or 0),
                        int(receipt.get("rejected_count") or 0),
                        int(receipt.get("dlq_count") or 0),
                        str(receipt.get("audit_id") or ""),
                        _json_dumps(receipt),
                    ),
                )

    def runtime_outbox_receipt_records(self) -> tuple[dict[str, Any], ...]:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT record
                    FROM agentops_runtime_outbox_receipts
                    ORDER BY batch_id, outbox_id
                    """
                )
                return tuple(_json_object(row[0]) for row in cursor.fetchall())

    def write_runtime_run_fact(
        self, event: dict[str, Any], payload: dict[str, Any]
    ) -> str:
        record = {
            **payload,
            "event_id": event["event_id"],
            "sequence_no": event.get("sequence_no", 0),
            "received_at": utc_now(),
        }
        run_id = str(payload["run_id"])
        attempt_identity = _runtime_attempt_identity(payload.get("attempt_no", 1))
        existing = self.get_runtime_run_fact(run_id)
        if (
            existing
            and _runtime_attempt_matches(
                existing.get("attempt_no"), payload.get("attempt_no", 1)
            )
            and _runtime_number_sort_value(record.get("sequence_no", 0))
            <= (_runtime_number_sort_value(existing.get("sequence_no", 0)))
        ):
            return "stale_ignored"
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO agentops_runtime_runs (
                      run_id, attempt_no_identity, event_id, trace_id, agent_id,
                      version, sequence_no, record
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (run_id, attempt_no_identity) DO UPDATE SET
                      event_id = EXCLUDED.event_id,
                      trace_id = EXCLUDED.trace_id,
                      agent_id = EXCLUDED.agent_id,
                      version = EXCLUDED.version,
                      sequence_no = EXCLUDED.sequence_no,
                      received_at = now(),
                      record = EXCLUDED.record
                    """,
                    (
                        run_id,
                        attempt_identity,
                        str(event["event_id"]),
                        str(payload.get("trace_id") or ""),
                        str(payload.get("agent_id") or ""),
                        str(
                            payload.get("version") or payload.get("agent_version") or ""
                        ),
                        _runtime_number_sort_value(event.get("sequence_no", 0)),
                        _json_dumps(record),
                    ),
                )
        return "stored"

    def get_runtime_run_fact(self, run_id: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT record
                    FROM agentops_runtime_runs
                    WHERE run_id = %s
                    ORDER BY sequence_no DESC, received_at DESC
                    LIMIT 1
                    """,
                    (run_id,),
                )
                row = cursor.fetchone()
        return _json_object(row[0]) if row else None

    def runtime_run_records_for_agent_version(
        self, agent_id: str, version: str, *, limit: int | None = None
    ) -> tuple[dict[str, Any], ...]:
        sql = """
            SELECT record
            FROM agentops_runtime_runs
            WHERE agent_id = %s AND version = %s
            ORDER BY received_at, sequence_no
        """
        params: tuple[Any, ...] = (agent_id, version)
        if limit is not None and limit > 0:
            sql += " LIMIT %s"
            params = (*params, limit)
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return tuple(_json_object(row[0]) for row in cursor.fetchall())

    def write_trace_span_fact(
        self, event: dict[str, Any], payload: dict[str, Any]
    ) -> str:
        record = {
            **payload,
            "event_id": event["event_id"],
            "sequence_no": event.get("sequence_no", 0),
            "received_at": utc_now(),
        }
        key_params = (
            str(payload["run_id"]),
            str(payload["trace_id"]),
            _runtime_attempt_identity(payload.get("attempt_no", 1)),
            str(payload["span_id"]),
        )
        existing = self._trace_span_record(*key_params)
        if existing and _runtime_number_sort_value(
            record.get("sequence_no", 0)
        ) <= _runtime_number_sort_value(existing.get("sequence_no", 0)):
            return "stale_ignored"
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO agentops_trace_spans (
                      run_id, trace_id, attempt_no_identity, span_id, event_id,
                      sequence_no, start_time, record
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (run_id, trace_id, attempt_no_identity, span_id)
                    DO UPDATE SET
                      event_id = EXCLUDED.event_id,
                      sequence_no = EXCLUDED.sequence_no,
                      start_time = EXCLUDED.start_time,
                      received_at = now(),
                      record = EXCLUDED.record
                    """,
                    (
                        *key_params,
                        str(event["event_id"]),
                        _runtime_number_sort_value(event.get("sequence_no", 0)),
                        str(payload.get("start_time") or ""),
                        _json_dumps(record),
                    ),
                )
        return "stored"

    def trace_span_records_for_run(
        self, run_id: str, *, attempt_no: Any | None = None
    ) -> tuple[dict[str, Any], ...]:
        sql = "SELECT record FROM agentops_trace_spans WHERE run_id = %s"
        params: tuple[Any, ...] = (run_id,)
        if attempt_no is not None:
            sql += " AND attempt_no_identity = %s"
            params = (*params, _runtime_attempt_identity(attempt_no))
        sql += " ORDER BY start_time, span_id"
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return tuple(_json_object(row[0]) for row in cursor.fetchall())

    def trace_span_records(self) -> tuple[dict[str, Any], ...]:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT record
                    FROM agentops_trace_spans
                    ORDER BY run_id, start_time, span_id
                    """
                )
                return tuple(_json_object(row[0]) for row in cursor.fetchall())

    def has_trace_span(
        self, run_id: str, trace_id: str, span_id: str, *, attempt_no: Any | None = None
    ) -> bool:
        sql = """
            SELECT 1
            FROM agentops_trace_spans
            WHERE run_id = %s AND trace_id = %s AND span_id = %s
        """
        params: tuple[Any, ...] = (run_id, trace_id, span_id)
        if attempt_no is not None:
            sql += " AND attempt_no_identity = %s"
            params = (*params, _runtime_attempt_identity(attempt_no))
        sql += " LIMIT 1"
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone() is not None

    def write_guardrail_result_fact(
        self, event: dict[str, Any], payload: dict[str, Any]
    ) -> str:
        record = {
            **payload,
            "event_id": event["event_id"],
            "sequence_no": event.get("sequence_no", 0),
            "received_at": utc_now(),
        }
        key_params = (
            str(payload["run_id"]),
            _runtime_attempt_identity(payload.get("attempt_no", 1)),
            str(payload["guardrail_result_id"]),
        )
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO agentops_guardrail_results (
                      run_id, attempt_no_identity, guardrail_result_id, event_id,
                      sequence_no, record
                    )
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (run_id, attempt_no_identity, guardrail_result_id)
                    DO UPDATE SET
                      event_id = EXCLUDED.event_id,
                      sequence_no = EXCLUDED.sequence_no,
                      received_at = now(),
                      record = EXCLUDED.record
                    """,
                    (
                        *key_params,
                        str(event["event_id"]),
                        _runtime_number_sort_value(event.get("sequence_no", 0)),
                        _json_dumps(record),
                    ),
                )
        return "stored"

    def guardrail_result_records_for_run(
        self, run_id: str, *, attempt_no: Any | None = None
    ) -> tuple[dict[str, Any], ...]:
        sql = "SELECT record FROM agentops_guardrail_results WHERE run_id = %s"
        params: tuple[Any, ...] = (run_id,)
        if attempt_no is not None:
            sql += " AND attempt_no_identity = %s"
            params = (*params, _runtime_attempt_identity(attempt_no))
        sql += " ORDER BY received_at, sequence_no, guardrail_result_id"
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return tuple(_json_object(row[0]) for row in cursor.fetchall())

    def write_runtime_dlq(
        self,
        event: dict[str, Any],
        *,
        error_code: str,
        message: str,
        state: str = "degraded",
        status: str = "dlq",
        retryable: bool = True,
    ) -> None:
        record = self._runtime_dlq_record(
            event, error_code, message, state, status, retryable
        )
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO agentops_runtime_dlq (
                      event_id, run_id, agent_id, version, event_type,
                      event_type_version, schema_version, sequence_no,
                      idempotency_key, payload_hash, payload_ref, source_trust,
                      integration_mode, status, state, error_code, message,
                      retryable, record
                    )
                    VALUES (
                      %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                      %s, %s, %s, %s, %s::jsonb
                    )
                    ON CONFLICT (event_id) DO UPDATE SET
                      run_id = EXCLUDED.run_id,
                      agent_id = EXCLUDED.agent_id,
                      version = EXCLUDED.version,
                      event_type = EXCLUDED.event_type,
                      event_type_version = EXCLUDED.event_type_version,
                      schema_version = EXCLUDED.schema_version,
                      sequence_no = EXCLUDED.sequence_no,
                      idempotency_key = EXCLUDED.idempotency_key,
                      payload_hash = EXCLUDED.payload_hash,
                      payload_ref = EXCLUDED.payload_ref,
                      source_trust = EXCLUDED.source_trust,
                      integration_mode = EXCLUDED.integration_mode,
                      status = EXCLUDED.status,
                      state = EXCLUDED.state,
                      error_code = EXCLUDED.error_code,
                      message = EXCLUDED.message,
                      retryable = EXCLUDED.retryable,
                      received_at = now(),
                      record = EXCLUDED.record
                    """,
                    (
                        record["event_id"],
                        record["run_id"],
                        record["agent_id"],
                        record["version"],
                        record["event_type"],
                        record["event_type_version"],
                        record["schema_version"],
                        record["sequence_no"],
                        record["idempotency_key"],
                        record["payload_hash"],
                        record["payload_ref"],
                        record["source_trust"],
                        record["integration_mode"],
                        record["status"],
                        record["state"],
                        record["error_code"],
                        record["message"],
                        record["retryable"],
                        _json_dumps(record),
                    ),
                )

    def runtime_dlq_count(self) -> int:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT count(*) FROM agentops_runtime_dlq")
                return int(cursor.fetchone()[0])

    def runtime_dlq_records(
        self, *, agent_id: str | None = None, version: str | None = None
    ) -> tuple[dict[str, Any], ...]:
        sql = "SELECT record FROM agentops_runtime_dlq WHERE true"
        params: tuple[Any, ...] = ()
        if agent_id is not None:
            sql += " AND agent_id = %s"
            params = (*params, agent_id)
        if version is not None:
            sql += " AND version = %s"
            params = (*params, version)
        sql += " ORDER BY received_at, event_id"
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return tuple(_json_object(row[0]) for row in cursor.fetchall())

    def _trace_span_record(
        self,
        run_id: str,
        trace_id: str,
        attempt_no_identity: str,
        span_id: str,
    ) -> dict[str, Any] | None:
        with self._connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT record
                    FROM agentops_trace_spans
                    WHERE run_id = %s
                      AND trace_id = %s
                      AND attempt_no_identity = %s
                      AND span_id = %s
                    """,
                    (run_id, trace_id, attempt_no_identity, span_id),
                )
                row = cursor.fetchone()
        return _json_object(row[0]) if row else None

    def _runtime_dlq_record(
        self,
        event: dict[str, Any],
        error_code: str,
        message: str,
        state: str,
        status: str,
        retryable: bool,
    ) -> dict[str, Any]:
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        run_id = str(event.get("run_id") or payload.get("run_id") or "")
        return {
            "event_id": str(event.get("event_id") or "unknown"),
            "run_id": run_id,
            "agent_id": str(event.get("agent_id") or payload.get("agent_id") or ""),
            "version": str(
                event.get("version")
                or event.get("agent_version")
                or payload.get("version")
                or payload.get("agent_version")
                or ""
            ),
            "event_type": str(event.get("event_type") or ""),
            "event_type_version": str(event.get("event_type_version") or ""),
            "schema_version": str(event.get("schema_version") or ""),
            "sequence_no": event.get("sequence_no"),
            "idempotency_key": str(event.get("idempotency_key") or ""),
            "payload_hash": str(event.get("payload_hash") or ""),
            "payload_ref": str(event.get("payload_ref") or ""),
            "source_trust": str(event.get("source_trust") or ""),
            "integration_mode": str(event.get("integration_mode") or ""),
            "status": status,
            "state": state,
            "error_code": error_code,
            "message": message,
            "retryable": retryable,
            "received_at": utc_now(),
        }

    @contextmanager
    def _connection(self) -> Iterator[Any]:
        existing = _RUNTIME_CONNECTION.get()
        if existing is not None:
            yield existing
            return
        with self._new_connection() as connection:
            yield connection

    def _new_connection(self) -> Any:
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover - exercised without driver.
            raise RuntimeError(
                "AGENTOPS_DATABASE_URL requires the optional psycopg PostgreSQL driver."
            ) from exc
        return psycopg.connect(
            self.database_url,
            connect_timeout=self.connect_timeout_seconds,
        )


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        decoded = json.loads(value)
        return decoded if isinstance(decoded, dict) else {}
    return {}
