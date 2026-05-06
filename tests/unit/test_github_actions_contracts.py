from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "agentops-cross-platform.yml"
ENGINEERING_DOC = ROOT / "docs" / "engineering" / "cross-platform-compatibility.md"


def _workflow_lines() -> list[str]:
    assert WORKFLOW.exists(), "AgentOps cross-platform workflow must exist"
    return [
        line.rstrip()
        for line in WORKFLOW.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    ]


def _job_block(job_name: str) -> list[str]:
    lines = _workflow_lines()
    start = next(i for i, line in enumerate(lines) if line == f"  {job_name}:")
    end = len(lines)
    for idx in range(start + 1, len(lines)):
        if re.match(r"^  [A-Za-z0-9_-]+:$", lines[idx]):
            end = idx
            break
    return lines[start:end]


def _step_block(job: list[str], step_name: str) -> list[str]:
    marker = f"      - name: {step_name}"
    start = next(i for i, line in enumerate(job) if line == marker)
    end = len(job)
    for idx in range(start + 1, len(job)):
        if job[idx].startswith("      - name: "):
            end = idx
            break
    return job[start:end]


def _matrix_values(job: list[str], key: str) -> list[str]:
    marker = f"        {key}:"
    start = next(i for i, line in enumerate(job) if line == marker)
    values: list[str] = []
    for line in job[start + 1 :]:
        if line.startswith("        ") and not line.startswith("          "):
            break
        match = re.match(r"^          - ['\"]?([^'\"]+)['\"]?$", line)
        if match:
            values.append(match.group(1))
    return values


def _block_text(lines: list[str]) -> str:
    return "\n".join(lines)


def test_cross_platform_workflow_covers_target_operating_systems() -> None:
    backend = _job_block("backend")
    frontend = _job_block("frontend")
    result = _job_block("compatibility-result")

    assert "    runs-on: ${{ matrix.os }}" in backend
    assert "    runs-on: ${{ matrix.os }}" in frontend
    assert _matrix_values(backend, "os") == ["ubuntu-latest", "macos-latest", "windows-latest"]
    assert _matrix_values(frontend, "os") == ["ubuntu-latest", "macos-latest", "windows-latest"]
    assert "      fail-fast: false" in backend
    assert "      fail-fast: false" in frontend
    assert "      - backend" in result
    assert "      - frontend" in result


def test_cross_platform_workflow_covers_backend_gates_in_backend_job() -> None:
    backend = _job_block("backend")

    assert _matrix_values(backend, "python-version") == ["3.11", "3.12"]
    assert "          python-version: ${{ matrix.python-version }}" in _step_block(backend, "Set up Python")
    assert "        run: uv sync --locked" in _step_block(backend, "Sync Python dependencies")
    assert "        run: uv run ruff check src tests" in _step_block(backend, "Ruff")
    assert "        run: uv run pytest tests -q" in _step_block(backend, "Pytest")
    assert "        run: uv build --sdist --wheel --out-dir dist/python" in _step_block(backend, "Build Python package")


def test_cross_platform_workflow_covers_frontend_gates_in_frontend_job() -> None:
    frontend = _job_block("frontend")

    assert _matrix_values(frontend, "node-version") == ["22", "24"]
    assert "        working-directory: apps/agentops-console" in frontend
    assert "          node-version: ${{ matrix.node-version }}" in _step_block(frontend, "Set up Node")
    assert "          cache-dependency-path: apps/agentops-console/package-lock.json" in _step_block(frontend, "Set up Node")
    assert "        run: npm ci --audit=false" in _step_block(frontend, "Install frontend dependencies")
    assert "        run: npm test" in _step_block(frontend, "Contract tests")
    assert "        run: npm run build" in _step_block(frontend, "Build")


def test_cross_platform_workflow_uploads_per_platform_packages() -> None:
    backend_upload = _block_text(_step_block(_job_block("backend"), "Upload Python package artifact"))
    frontend_upload = _block_text(_step_block(_job_block("frontend"), "Upload console package artifact"))

    assert "uses: actions/upload-artifact@v4" in backend_upload
    assert "name: agentops-python-${{ matrix.os }}-py${{ matrix.python-version }}" in backend_upload
    assert "path: dist/python/*" in backend_upload
    assert "if-no-files-found: error" in backend_upload

    assert "uses: actions/upload-artifact@v4" in frontend_upload
    assert "name: agentops-console-${{ matrix.os }}-node${{ matrix.node-version }}" in frontend_upload
    assert "path: apps/agentops-console/dist/**" in frontend_upload
    assert "if-no-files-found: error" in frontend_upload


def test_cross_platform_engineering_constraints_are_documented() -> None:
    assert ENGINEERING_DOC.exists(), "Cross-platform engineering constraints must be documented"
    doc = ENGINEERING_DOC.read_text(encoding="utf-8")

    assert "目标平台证据" in doc
    assert "Windows" in doc
    assert "Linux" in doc
    assert "macOS" in doc
    assert "vendor/enterprise-vue2" in doc
    assert "npm ci --audit=false" in doc
    assert "npm audit" in doc
    assert "云端打包" in doc
    assert "agentops-python-<os>-py<version>" in doc
    assert "agentops-console-<os>-node<version>" in doc
