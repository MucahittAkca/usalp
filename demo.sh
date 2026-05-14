#!/usr/bin/env bash
set -euo pipefail

export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-usalp_demo_password}"
export LLM_API_KEY="${LLM_API_KEY:-}"
export AGENT_API_KEY="${AGENT_API_KEY:-usalp-demo-agent-key}"
export SECRET_KEY="${SECRET_KEY:-usalp_demo_secret_key_change_before_production_32}"
export DASHBOARD_USERNAME="${DASHBOARD_USERNAME:-admin}"
export DASHBOARD_PASSWORD="${DASHBOARD_PASSWORD:-admin}"
export DASHBOARD_PASSWORD_HASH="${DASHBOARD_PASSWORD_HASH:-}"
export ENVIRONMENT="${ENVIRONMENT:-development}"
export DEMO_MODE="${DEMO_MODE:-true}"
export DEMO_SEED_RESET="${DEMO_SEED_RESET:-true}"
export ALERT_NOTIFICATIONS_ENABLED="${ALERT_NOTIFICATIONS_ENABLED:-false}"
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-usalp_demo}"

echo "Usalp demo modu baslatiliyor..."
echo "Compose project: ${COMPOSE_PROJECT_NAME}"
echo "Dashboard: http://localhost"
echo "Kullanici: ${DASHBOARD_USERNAME}"
echo "Sifre: ${DASHBOARD_PASSWORD}"
echo
echo "Demo verisi backend startup sirasinda hazirlanir."
echo "Durdurmak icin Ctrl+C."
echo "Demo container ve volume temizligi icin: docker compose -p ${COMPOSE_PROJECT_NAME} down -v"
echo

docker compose -p "${COMPOSE_PROJECT_NAME}" up --build
