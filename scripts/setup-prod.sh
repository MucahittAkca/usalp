#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/setup-prod.sh [--force] [--skip-dns-check]
       ./scripts/setup-prod.sh --reset-dashboard-password

Creates a production .env file, validates host prerequisites, then runs:
  docker compose up -d --build

Maintenance:
  --reset-dashboard-password  Prompt for dashboard credentials, update .env,
                              recreate backend, then verify login.

Optional environment variables:
  USALP_DOMAIN              Public DNS name for this control plane
  ACME_EMAIL                Let's Encrypt contact email
  DASHBOARD_USERNAME        Dashboard username (default: admin)
  DASHBOARD_PASSWORD        Dashboard password (prompted if empty)
  LLM_API_KEY               Optional LLM API key
EOF
}

FORCE=false
SKIP_DNS_CHECK=false
RESET_DASHBOARD_PASSWORD=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=true; shift ;;
    --skip-dns-check) SKIP_DNS_CHECK=true; shift ;;
    --reset-dashboard-password) RESET_DASHBOARD_PASSWORD=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

prompt_value() {
  local var_name="$1"
  local prompt="$2"
  local default_value="${3:-}"
  local value="${!var_name:-}"
  if [[ -n "$value" ]]; then
    printf '%s' "$value"
    return
  fi
  if [[ -n "$default_value" ]]; then
    read -r -p "$prompt [$default_value]: " value
    printf '%s' "${value:-$default_value}"
  else
    read -r -p "$prompt: " value
    printf '%s' "$value"
  fi
}

prompt_secret() {
  local var_name="$1"
  local prompt="$2"
  local value="${!var_name:-}"
  if [[ -z "$value" ]]; then
    read -r -s -p "$prompt: " value
    echo
  fi
  printf '%s' "$value"
}

prompt_secret_confirm() {
  local var_name="$1"
  local prompt="$2"
  local value="${!var_name:-}"
  local confirm

  if [[ -n "$value" ]]; then
    printf '%s' "$value"
    return
  fi

  while true; do
    read -r -s -p "$prompt: " value
    echo
    read -r -s -p "$prompt (again): " confirm
    echo

    if [[ "$value" == "$confirm" ]]; then
      printf '%s' "$value"
      return
    fi

    echo "Dashboard passwords did not match. Please try again." >&2
  done
}

json_string() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//$'\n'/\\n}"
  value="${value//$'\r'/\\r}"
  value="${value//$'\t'/\\t}"
  printf '"%s"' "$value"
}

verify_dashboard_login() {
  local domain="$1"
  local username="$2"
  local password="$3"
  local payload

  payload="{\"username\":$(json_string "$username"),\"password\":$(json_string "$password")}"
  printf '%s' "$payload" | curl -fsS --max-time 10 \
    -H "Content-Type: application/json" \
    --data-binary @- \
    "https://${domain}/api/v1/auth/token" >/dev/null
}

wait_for_ready_and_verify() {
  local domain="$1"
  local username="$2"
  local password="$3"

  echo "Waiting for https://${domain}/health ..."
  for _ in $(seq 1 60); do
    if curl -fsS --max-time 5 "https://${domain}/health" >/dev/null; then
      if ! verify_dashboard_login "$domain" "$username" "$password"; then
        echo "Health check passed, but dashboard login self-check failed." >&2
        echo "Backend is reachable, but the stored dashboard credentials do not match the provided credentials." >&2
        echo "Reset them with: ./scripts/setup-prod.sh --reset-dashboard-password" >&2
        echo "Inspect auth logs with: docker compose logs -f backend" >&2
        exit 1
      fi
      echo "Dashboard credentials verified."
      echo "Dashboard username: ${username}"
      echo "If browser login returns 401, reset with: ./scripts/setup-prod.sh --reset-dashboard-password"
      echo "Usalp is ready: https://${domain}"
      return
    fi
    sleep 5
  done

  echo "Containers started, but health check did not become ready within 5 minutes." >&2
  echo "Check logs with: docker compose logs -f caddy backend" >&2
  exit 1
}

random_secret() {
  openssl rand -base64 36 | tr -d '\n'
}

hash_password() {
  local password="$1"
  local salt
  salt="$(openssl rand -hex 8)"
  openssl passwd -6 -salt "$salt" "$password"
}

check_port_free() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    if ss -ltn | awk '{print $4}' | grep -Eq "(:|\\])${port}$"; then
      echo "Port $port is already in use. Stop the existing service before setup." >&2
      exit 1
    fi
  fi
}

validate_dashboard_username() {
  local username="$1"

  if [[ -z "$username" ]]; then
    echo "Dashboard username cannot be empty." >&2
    return 1
  fi
  if [[ ${#username} -gt 150 ]]; then
    echo "Dashboard username must be at most 150 characters." >&2
    return 1
  fi
  if [[ ! "$username" =~ ^[A-Za-z0-9._@+-]+$ ]]; then
    echo "Dashboard username may only contain letters, numbers, '.', '_', '@', '+', and '-'." >&2
    return 1
  fi
}

validate_dashboard_password() {
  local password="$1"

  if [[ ${#password} -lt 12 ]]; then
    echo "Dashboard password must be at least 12 characters." >&2
    return 1
  fi
  if [[ "$password" =~ ^[[:space:]] || "$password" =~ [[:space:]]$ ]]; then
    echo "Dashboard password must not start or end with whitespace." >&2
    echo "Leading/trailing spaces are invisible in browser login and commonly cause 401 errors." >&2
    return 1
  fi
  if [[ "$password" =~ [[:cntrl:]] ]]; then
    echo "Dashboard password must not contain control characters." >&2
    return 1
  fi
}

get_env_value() {
  local key="$1"
  local file="${2:-.env}"
  local line
  local value
  local first
  local last

  line="$(grep -E "^${key}=" "$file" | tail -n 1 || true)"
  if [[ -z "$line" ]]; then
    return
  fi

  value="${line#*=}"
  if [[ ${#value} -ge 2 ]]; then
    first="${value:0:1}"
    last="${value: -1}"
    if [[ "$first" == "$last" && ( "$first" == "'" || "$first" == '"' ) ]]; then
      value="${value:1:${#value}-2}"
    fi
  fi
  printf '%s' "$value"
}

set_env_value() {
  local key="$1"
  local value="$2"
  local file="${3:-.env}"
  local tmp
  local found=false
  local line

  tmp="$(mktemp "${file}.tmp.XXXXXX")"
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" == "${key}="* ]]; then
      printf '%s=%s\n' "$key" "$value" >> "$tmp"
      found=true
    else
      printf '%s\n' "$line" >> "$tmp"
    fi
  done < "$file"

  if [[ "$found" != "true" ]]; then
    printf '%s=%s\n' "$key" "$value" >> "$tmp"
  fi

  mv "$tmp" "$file"
  chmod 600 "$file"
}

domain_from_env() {
  local url
  local domain

  url="$(get_env_value USALP_PUBLIC_URL)"
  if [[ "$url" == https://* ]]; then
    domain="${url#https://}"
    domain="${domain%%/*}"
    printf '%s' "$domain"
    return
  fi

  domain="$(get_env_value USALP_SITE_ADDRESS)"
  domain="${domain#https://}"
  domain="${domain#http://}"
  domain="${domain%%/*}"
  printf '%s' "$domain"
}

write_dashboard_credentials_env() {
  local username="$1"
  local password_hash="$2"

  set_env_value DASHBOARD_USERNAME "$username"
  set_env_value DASHBOARD_PASSWORD ""
  set_env_value DASHBOARD_PASSWORD_HASH "'${password_hash}'"
}

reset_dashboard_password() {
  local existing_username
  local dashboard_user
  local dashboard_pass
  local dashboard_password_hash
  local domain

  if [[ ! -f .env ]]; then
    echo ".env does not exist. Run ./scripts/setup-prod.sh first." >&2
    exit 1
  fi

  existing_username="$(get_env_value DASHBOARD_USERNAME)"
  dashboard_user="$(prompt_value DASHBOARD_USERNAME "Dashboard username" "${existing_username:-admin}")"
  dashboard_pass="$(prompt_secret_confirm DASHBOARD_PASSWORD "New dashboard password")"

  validate_dashboard_username "$dashboard_user" || exit 1
  validate_dashboard_password "$dashboard_pass" || exit 1

  dashboard_password_hash="$(hash_password "$dashboard_pass")"
  umask 077
  write_dashboard_credentials_env "$dashboard_user" "$dashboard_password_hash"

  echo "Updated .env dashboard credentials."
  docker compose up -d --force-recreate backend

  domain="$(domain_from_env)"
  if [[ -z "$domain" || "$domain" == :* ]]; then
    echo "Could not determine production domain from USALP_PUBLIC_URL or USALP_SITE_ADDRESS." >&2
    echo "Credentials were updated. Verify manually with: docker compose logs -f backend" >&2
    exit 1
  fi

  wait_for_ready_and_verify "$domain" "$dashboard_user" "$dashboard_pass"
}

require_cmd curl
require_cmd docker
require_cmd openssl
docker compose version >/dev/null

if [[ "$RESET_DASHBOARD_PASSWORD" == "true" ]]; then
  reset_dashboard_password
  exit 0
fi

if [[ -f .env && "$FORCE" != "true" ]]; then
  echo ".env already exists. Re-run with --force to replace it." >&2
  exit 1
fi

DOMAIN="$(prompt_value USALP_DOMAIN "Domain for Usalp")"
ACME_MAIL="$(prompt_value ACME_EMAIL "Let's Encrypt email")"
DASHBOARD_USER="$(prompt_value DASHBOARD_USERNAME "Dashboard username" "admin")"
DASHBOARD_PASS="$(prompt_secret_confirm DASHBOARD_PASSWORD "Dashboard password")"
LLM_KEY="${LLM_API_KEY:-}"

if [[ ! "$DOMAIN" =~ ^[A-Za-z0-9.-]+$ || "$DOMAIN" != *.* ]]; then
  echo "USALP_DOMAIN must be a real DNS name, for example monitoring.example.com." >&2
  exit 1
fi
if [[ "$DOMAIN" =~ (^localhost$|^127\.|^10\.|^192\.168\.|^172\.(1[6-9]|2[0-9]|3[01])\.) ]]; then
  echo "Production setup requires a public domain, not localhost or a private IP." >&2
  exit 1
fi
if [[ -z "$ACME_MAIL" || "$ACME_MAIL" != *@* ]]; then
  echo "ACME_EMAIL must be a valid contact email." >&2
  exit 1
fi
validate_dashboard_username "$DASHBOARD_USER" || exit 1
validate_dashboard_password "$DASHBOARD_PASS" || exit 1

if [[ "$SKIP_DNS_CHECK" != "true" ]]; then
  getent ahosts "$DOMAIN" >/dev/null || {
    echo "DNS lookup failed for $DOMAIN. Point the domain at this host before setup." >&2
    exit 1
  }
fi

check_port_free 80
check_port_free 443

curl -fsS --max-time 10 https://acme-v02.api.letsencrypt.org/directory >/dev/null || {
  echo "Outbound HTTPS to Let's Encrypt failed." >&2
  exit 1
}

POSTGRES_PASSWORD="$(random_secret)"
SECRET_KEY="$(openssl rand -hex 32)"
DASHBOARD_PASSWORD_HASH="$(hash_password "$DASHBOARD_PASS")"

umask 077
cat > .env <<EOF
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
LLM_API_KEY=${LLM_KEY}
LLM_BASE_URL=https://openrouter.ai/api
LLM_MODEL=anthropic/claude-sonnet-4

ENVIRONMENT=production
USALP_PUBLIC_URL=https://${DOMAIN}
USALP_SITE_ADDRESS=${DOMAIN}
ACME_EMAIL=${ACME_MAIL}
CORS_ORIGINS=https://${DOMAIN}
MAX_REQUEST_BODY_BYTES=1048576
MAX_REQUEST_BODY_SIZE=10MB

SECRET_KEY=${SECRET_KEY}
DASHBOARD_USERNAME=${DASHBOARD_USER}
DASHBOARD_PASSWORD=
DASHBOARD_PASSWORD_HASH='${DASHBOARD_PASSWORD_HASH}'
JWT_EXPIRE_HOURS=24

SERVER_OFFLINE_AFTER_SECONDS=120
METRIC_RETENTION_DAYS=30
LOG_RETENTION_DAYS=14
SERVICE_STATUS_RETENTION_DAYS=7
AI_ANALYSIS_RETENTION_DAYS=90
RETENTION_SWEEP_INTERVAL_SECONDS=3600

ALERT_NOTIFICATIONS_ENABLED=true
ALERT_NOTIFICATION_TIMEOUT_SECONDS=5
ALERT_EMAIL_HOST=
ALERT_EMAIL_PORT=587
ALERT_EMAIL_USERNAME=
ALERT_EMAIL_PASSWORD=
ALERT_EMAIL_FROM=
ALERT_EMAIL_TO=
ALERT_EMAIL_USE_SSL=false
ALERT_EMAIL_STARTTLS=true
ALERT_TELEGRAM_BOT_TOKEN=
ALERT_TELEGRAM_CHAT_ID=
ALERT_SLACK_WEBHOOK_URL=

DEMO_MODE=false
DEMO_SEED_RESET=true
NEXT_PUBLIC_API_URL=/api/v1
EOF

echo "Created .env with production defaults."
docker compose up -d --build

wait_for_ready_and_verify "$DOMAIN" "$DASHBOARD_USER" "$DASHBOARD_PASS"
