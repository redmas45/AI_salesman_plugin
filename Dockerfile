FROM node:22-alpine AS crm-build

WORKDIR /workspace

RUN corepack enable

COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY packages/contracts/package.json packages/contracts/package.json
COPY crm/package.json crm/package.json
COPY plugin/package.json plugin/package.json
RUN corepack pnpm install --filter ai-hub-crm --filter @ai-hub/contracts --frozen-lockfile

COPY packages/contracts packages/contracts
COPY crm crm
RUN corepack pnpm --filter ai-hub-crm build


FROM node:22-alpine AS client-panel-build

WORKDIR /client-panel

COPY --from=client_panel_context package*.json ./
RUN npm install

COPY --from=client_panel_context . ./
RUN npm run build


FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV CLIENT_PANEL_SOURCE_DIR=/app/client_panel

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ffmpeg \
        git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip \
    && pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu \
    && pip install sentence-transformers playwright crawl4ai \
    && playwright install --with-deps chromium \
    && crawl4ai-setup

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
COPY --from=crm-build /workspace/crm/dist /app/crm/dist
COPY --from=client-panel-build /client-panel/dist /app/client_panel/dist
RUN chmod +x /app/docker/entrypoint.sh

EXPOSE 8585

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8585"]
