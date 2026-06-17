FROM node:22-alpine AS crm-build

WORKDIR /crm

COPY crm/package*.json ./
RUN npm install

COPY crm ./
RUN npm run build


FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ffmpeg \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && crawl4ai-setup

COPY . .
COPY --from=crm-build /crm/dist /app/crm/dist
RUN chmod +x /app/docker/entrypoint.sh

EXPOSE 8585

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8585"]
