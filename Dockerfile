FROM python:3.12-slim AS agentops-api

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir ".[postgres]"

EXPOSE 8765
CMD ["python", "-m", "agentops.api.server", "--host", "0.0.0.0", "--port", "8765", "--require-auth"]


FROM python:3.12-slim AS agentops-gateway

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir .

EXPOSE 8766
CMD ["python", "-m", "agentops.api.gateway", "--host", "0.0.0.0", "--port", "8766"]


FROM node:24-alpine AS agentops-console

WORKDIR /app
COPY vendor ./vendor
COPY apps/agentops-console ./apps/agentops-console

WORKDIR /app/apps/agentops-console
ARG VITE_AGENTOPS_API_BASE=http://127.0.0.1:8766
ENV VITE_AGENTOPS_API_BASE=${VITE_AGENTOPS_API_BASE}

RUN npm ci && npm run build

EXPOSE 4173
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "4173"]
