#!/usr/bin/env bash
# Usalp Agent Kurulum Scripti
# Kullanım: curl -fsSL http://<backend>/install.sh | bash -s -- --api-key <KEY> --backend-url http://<backend>

set -euo pipefail

# --------------------------------------------------------------------------
# Argümanları parse et
# --------------------------------------------------------------------------

API_KEY=""
BACKEND_URL=""
INSTALL_DIR="/opt/usalp-agent"
SERVICE_NAME="usalp-agent"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-key)      API_KEY="$2";      shift 2 ;;
    --backend-url)  BACKEND_URL="$2";  shift 2 ;;
    --install-dir)  INSTALL_DIR="$2";  shift 2 ;;
    *) echo "Bilinmeyen parametre: $1"; exit 1 ;;
  esac
done

if [[ -z "$API_KEY" || -z "$BACKEND_URL" ]]; then
  echo "Hata: --api-key ve --backend-url zorunludur."
  echo "Kullanım: install.sh --api-key <KEY> --backend-url http://<IP>"
  exit 1
fi

# --------------------------------------------------------------------------
# Renk kodları
# --------------------------------------------------------------------------

GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
NC="\033[0m"

info()    { echo -e "${GREEN}[✓]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
error()   { echo -e "${RED}[✗]${NC} $*"; exit 1; }

# --------------------------------------------------------------------------
# Ön koşul kontrolleri
# --------------------------------------------------------------------------

info "Usalp Agent kurulumu başlıyor..."
info "Backend: $BACKEND_URL"

if [[ $EUID -ne 0 ]]; then
  error "Bu script root yetkisi gerektirir. 'sudo bash install.sh ...' ile çalıştırın."
fi

command -v python3 >/dev/null 2>&1 || error "Python 3 bulunamadı. 'apt install python3' ile kurun."
command -v pip3   >/dev/null 2>&1 || warn "pip3 bulunamadı, kurulmaya çalışılacak..."

PYTHON_VERSION=$(python3 -c "import sys; print(sys.version_info.minor)")
if [[ "$PYTHON_VERSION" -lt 10 ]]; then
  error "Python 3.10+ gereklidir. Mevcut: 3.$PYTHON_VERSION"
fi

# --------------------------------------------------------------------------
# Kurulum dizinini oluştur
# --------------------------------------------------------------------------

info "Kurulum dizini oluşturuluyor: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# --------------------------------------------------------------------------
# Agent dosyalarını indir / kopyala
# --------------------------------------------------------------------------

# Eğer script agent klasöründen çalışıyorsa doğrudan kopyala
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -f "$SCRIPT_DIR/main.py" ]]; then
  info "Agent dosyaları $INSTALL_DIR konumuna kopyalanıyor..."
  cp -r "$SCRIPT_DIR"/. "$INSTALL_DIR/"
else
  # Yoksa backend'den indir
  info "Agent dosyaları backend'den indiriliyor..."
  curl -fsSL "$BACKEND_URL/agent.tar.gz" -o /tmp/usalp-agent.tar.gz \
    || error "Agent paketi indirilemedi: $BACKEND_URL/agent.tar.gz"
  tar -xzf /tmp/usalp-agent.tar.gz -C "$INSTALL_DIR" --strip-components=1
  rm /tmp/usalp-agent.tar.gz
fi

# --------------------------------------------------------------------------
# Python bağımlılıklarını kur
# --------------------------------------------------------------------------

info "Python bağımlılıkları kuruluyor..."
pip3 install --quiet --no-cache-dir \
  "pyyaml>=6.0" \
  "psutil>=6.0" \
  "httpx>=0.27" \
  "pydantic>=2.0" \
  "structlog>=24.0" \
  "tenacity>=9.0" \
  "schedule>=1.2" \
  || error "Bağımlılık kurulumu başarısız."

# --------------------------------------------------------------------------
# Hostname ve IP tespiti
# --------------------------------------------------------------------------

HOSTNAME_VAL=$(hostname -f 2>/dev/null || hostname)
IP_VAL=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

# --------------------------------------------------------------------------
# agent.yaml oluştur
# --------------------------------------------------------------------------

info "agent.yaml yapılandırması oluşturuluyor..."

cat > "$INSTALL_DIR/agent.yaml" <<EOF
server_id: ${HOSTNAME_VAL}
backend_url: ${BACKEND_URL}
api_key: ${API_KEY}

intervals:
  fast: 30
  slow: 60

services:
  - nginx
  - docker
  - postgresql
  - redis
  - mysql

log_files:
  - path: /var/log/syslog
    tail_lines: 100
    min_level: WARNING
  - path: /var/log/nginx/error.log
    tail_lines: 50
    min_level: ERROR
EOF

info "Yapılandırma: $INSTALL_DIR/agent.yaml"

# --------------------------------------------------------------------------
# systemd servis dosyasını oluştur
# --------------------------------------------------------------------------

info "systemd servis dosyası oluşturuluyor..."

cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=Usalp Monitoring Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=python3 ${INSTALL_DIR}/main.py --config ${INSTALL_DIR}/agent.yaml
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=PYTHONPATH=${INSTALL_DIR}
Environment=LOG_LEVEL=INFO

[Install]
WantedBy=multi-user.target
EOF

# --------------------------------------------------------------------------
# Servisi etkinleştir ve başlat
# --------------------------------------------------------------------------

info "Servis etkinleştiriliyor ve başlatılıyor..."
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

sleep 2

if systemctl is-active --quiet "$SERVICE_NAME"; then
  info "Usalp Agent başarıyla kuruldu ve çalışıyor!"
  echo ""
  echo -e "  ${GREEN}Servis durumu:${NC} systemctl status $SERVICE_NAME"
  echo -e "  ${GREEN}Loglar:${NC}        journalctl -u $SERVICE_NAME -f"
  echo ""
  echo -e "  Dashboard'da 30 saniye içinde bu sunucu görünecek:"
  echo -e "  ${GREEN}$BACKEND_URL${NC}"
else
  warn "Servis başlatılamadı. Log kontrol edin:"
  echo "  journalctl -u $SERVICE_NAME -n 30 --no-pager"
  exit 1
fi
