#!/usr/bin/env bash
set -euo pipefail

read_env_value() {
  local name="$1"
  local file="${2:-.env}"
  [[ -f "$file" ]] || return 0
  awk -F= -v key="$name" '
    $1 == key {
      sub(/^[^=]*=/, "")
      gsub(/^"|"$/, "")
      print
      exit
    }
  ' "$file"
}

if [[ -z "${LLM_API_KEY:-}" ]]; then
  LLM_API_KEY="$(read_env_value LLM_API_KEY)"
fi

export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-usalp_demo_password}"
if [[ "${LLM_API_KEY:-}" == "sk-or-v1-..." ]]; then
  LLM_API_KEY=""
fi
export LLM_API_KEY="${LLM_API_KEY:-}"
export LLM_BASE_URL="${LLM_BASE_URL:-https://openrouter.ai/api}"
export LLM_MODEL="${LLM_MODEL:-anthropic/claude-sonnet-4}"
export SECRET_KEY="${SECRET_KEY:-usalp_demo_secret_key_change_before_production_32}"
export DASHBOARD_USERNAME="${DASHBOARD_USERNAME:-admin}"
export DASHBOARD_PASSWORD="${DASHBOARD_PASSWORD:-admin}"
export DASHBOARD_PASSWORD_HASH="${DASHBOARD_PASSWORD_HASH:-}"
export ENVIRONMENT="${ENVIRONMENT:-development}"
export USALP_PUBLIC_URL="${USALP_PUBLIC_URL:-http://localhost}"
export USALP_SITE_ADDRESS="${USALP_SITE_ADDRESS:-:80}"
export ACME_EMAIL="${ACME_EMAIL:-admin@example.invalid}"
export CORS_ORIGINS="${CORS_ORIGINS:-http://localhost,http://localhost:3000}"
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-/api/v1}"
export DEMO_MODE="${DEMO_MODE:-true}"
export DEMO_SEED_RESET="${DEMO_SEED_RESET:-true}"
export ALERT_NOTIFICATIONS_ENABLED="${ALERT_NOTIFICATIONS_ENABLED:-false}"
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-usalp_demo}"

echo "Usalp demo modu baslatiliyor..."
echo "Compose project: ${COMPOSE_PROJECT_NAME}"
echo "Dashboard: http://localhost"
echo "Kullanici: ${DASHBOARD_USERNAME}"
echo "Sifre: ${DASHBOARD_PASSWORD}"
if [[ -n "${LLM_API_KEY}" ]]; then
  echo "LLM: ${LLM_BASE_URL} (${LLM_MODEL})"
else
  echo "LLM: devre disi (OpenRouter key yok)"
fi
echo
echo "Demo verisi backend startup sirasinda hazirlanir; [DEMO] etiketli ornek AI analizler seed edilir."
echo "Gercek yeni AI analiz icin .env dosyasina LLM_API_KEY=sk-or-v1-... ekleyin."
echo "LLM hatalari icin backend loglarini izleyin: docker compose -p ${COMPOSE_PROJECT_NAME} logs -f backend"
echo "Durdurmak icin Ctrl+C."
echo "Demo container ve volume temizligi icin: docker compose -p ${COMPOSE_PROJECT_NAME} down -v"
echo

docker compose -p "${COMPOSE_PROJECT_NAME}" down --remove-orphans
docker compose -p "${COMPOSE_PROJECT_NAME}" up --build --remove-orphans
