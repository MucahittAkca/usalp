# Usalp

AI destekli Linux sunucu izleme ve log analiz platformu.

## Mimari

- `backend`: FastAPI, PostgreSQL, Alembic, JWT auth, alert motoru ve AI analiz.
- `agent`: İzlenen Linux sunucuda çalışan metrik/log/servis toplayıcı.
- `dashboard`: Next.js dashboard.
- `caddy`: Dashboard ve API reverse proxy, production'da otomatik HTTPS.

## Production Kurulum

Merkezi kontrol düzlemi için bir Linux sunucu, gerçek DNS kaydı ve 80/443
portlarının açık olması gerekir.

Boş bir Ubuntu sunucuda önce temel araçları ve Docker Compose v2 eklentisini
kurun:

```bash
apt update
apt install -y git curl openssl docker.io docker-compose-plugin
systemctl enable --now docker
docker compose version
```

Kalıcı production için domain kullanılması önerilir. Geçici testte kendi domaininiz
yoksa public IP'yi çözen `sslip.io` formatı kullanılabilir:

```text
167.233.57.73.sslip.io
```

```bash
git clone https://github.com/MucahittAkca/usalp.git /opt/usalp
cd /opt/usalp
./scripts/setup-prod.sh
```

Script `.env` üretir, dashboard şifresini hash'ler, production secret'larını
oluşturur, DNS/port/outbound HTTPS kontrollerini yapar ve `docker compose up -d --build`
çalıştırır. Health hazır olduktan sonra kurulumda girilen dashboard kullanıcı
adı/şifresiyle auth self-check yapar. Dashboard ve API aynı origin üzerinden
servis edilir:

- Dashboard: `https://domain`
- Health: `https://domain/health`
- API: `https://domain/api/v1`

Browser'dan girişte 401 alınıyorsa backend çalışıyor ama browser'dan gönderilen
bilgiler kurulumda girilen bilgilerle eşleşmiyor demektir. Kullanıcı adı
büyük/küçük harfe duyarlıdır; setup script'i görünmez boşluk kaynaklı hataları
engellemek için kullanıcı adını sınırlar ve şifrenin başında/sonunda boşluk
kabul etmez. Tek komutla yeni dashboard kullanıcı adı/şifresi üretip backend
üzerinden doğrulamak için:

```bash
./scripts/setup-prod.sh --reset-dashboard-password
```

Geliştirme modunda hot reload ve localhost HTTP için:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Dashboard: `http://localhost`

API dokümantasyonu development ortamında: `http://localhost/api/docs`

## Demo Modu

Örnek sunucular, metrik geçmişi, loglar ve alert'lerle çalışan demo ortamını
tek komutla başlatmak için:

```bash
./demo.sh
```

LLM analizi opsiyoneldir. Gerçek AI analizi denemek için `.env` içine
OpenRouter anahtarını ekleyin:

```bash
LLM_API_KEY=sk-or-v1-...
```

Dashboard: `http://localhost`

Demo kullanıcı bilgileri:

- Kullanıcı: `admin`
- Şifre: `admin`

Demo modu `DEMO_MODE=true` ile backend startup sırasında seed verisini üretir.
Dashboard'un AI ekranı boş kalmasın diye demo verisiyle uyumlu örnek AI analiz
kayıtları da seed edilir; bu kayıtların özetinde `[DEMO]` etiketi bulunur.
`LLM_API_KEY` tanımlıysa dashboard'daki "Yeni Analiz Başlat" akışı gerçek LLM
çağrısı yapar ve yeni analizleri OpenRouter yanıtından üretir. Key tanımlı
değilse uygulama çalışmaya devam eder. LLM hataları backend loglarında görünür:

```bash
docker compose -p usalp_demo logs -f backend
```

Varsayılan olarak yalnızca `.usalp.demo` hostname suffix'li demo kayıtları
yenilenir; kullanıcı tarafından oluşturulan kayıtlar korunur. Demo verisini
her başlangıçta yenilememek için `DEMO_SEED_RESET=false` verilebilir.
Demo script'i varsayılan olarak `usalp_demo` Compose project adıyla ayrı volume
kullanır. Demo ortamını tamamen temizlemek için:

```bash
docker compose -p usalp_demo down -v
```

## Gerçek AI/LLM Kullanımı

Gerçek AI analizi için OpenRouter uyumlu bir API anahtarını `.env` dosyasına
yazın ve backend'i yeniden oluşturun:

```bash
cd /opt/usalp
nano .env
```

```bash
LLM_API_KEY=sk-or-v1-...
LLM_BASE_URL=https://openrouter.ai/api
LLM_MODEL=anthropic/claude-sonnet-4
```

```bash
docker compose up -d --force-recreate backend
docker compose logs -f backend
```

## Agent Kurulumu

Dashboard'da yeni sunucu ekleyince tek kullanımlık API anahtarı ve kurulum komutu
üretilir. İzlenecek Linux sunucuda bu komutu root yetkisiyle çalıştırın.

Agent kurulacak sunucuda systemd, outbound HTTPS erişimi, Python 3.12+, `venv`,
`curl` ve `tar` gerekir. Boş bir Ubuntu sunucuda:

```bash
apt update
apt install -y curl tar python3 python3-venv
```

Production komutu şu formdadır:

```bash
curl -fsSL https://domain/install.sh | sudo bash -s -- --api-key <key> --backend-url https://domain
```

Backend ayrıca kurulum için iki public dosya servis eder:

- `/install.sh`
- `/agent.tar.gz`

Installer plain HTTP backend URL'lerini reddeder; yalnızca lokal geliştirme için
`--allow-insecure` verilebilir. Agent runtime dosyaları `/opt/usalp-agent`,
config dosyası `/etc/usalp-agent/agent.yaml`, disk kuyruğu
`/var/lib/usalp-agent/queue` altında tutulur.

Kurulumdan sonra durum ve log kontrolü:

```bash
systemctl status usalp-agent --no-pager
journalctl -u usalp-agent -n 50 --no-pager
```

Yardımcı komutlar:

```bash
sudo bash /opt/usalp-agent/install.sh --status
sudo bash /opt/usalp-agent/install.sh --uninstall
```

Agent varsayılan olarak 30 saniyede bir CPU, RAM, network, servis ve yeni logları;
60 saniyede bir disk ve process verilerini gönderir.

Agent her payload'ı önce local disk kuyruğuna yazar, sonra backend'e gönderir.
Ağ veya 5xx hatasında veri `queue.dir` altında kalır ve sonraki döngülerde FIFO
sırayla tekrar gönderilir. Varsayılan kuyruk ayarı `queue/max_items=1000` ve
`flush_batch_size=25` değerlerini kullanır.

## Durum ve Alert Mantığı

- Sunucu ilk eklendiğinde `offline` olur.
- Agent metrik gönderince `online` olur ve `last_seen` güncellenir.
- Aktif alert varsa sunucu `warning` olarak görünür.
- Sunucular `environment`, `group_name` ve `tags` alanlarıyla ortam, grup ve
  etiket bazında ayrılabilir; dashboard sunucu listesi bu alanlarla filtrelenir.
- `SERVER_OFFLINE_AFTER_SECONDS` boyunca heartbeat gelmezse sunucu `offline` olur.
- Alert'ler `dedupe_key` ile tekilleştirilir; warning alert critical seviyeye
  yükselirse mevcut alert güncellenir ve AI analiz tetiklenir.
- Yeni veya güncellenen alert'ler e-posta, Telegram ve Slack kanallarına
  gönderilebilir. `.env` içinde ilgili kanalın zorunlu alanları boşsa kanal
  devre dışı kalır; `ALERT_NOTIFICATIONS_ENABLED=false` tüm gönderimleri kapatır.
- AI analiz yanıtları olası nedenlere ek olarak kanıt satırları ve önerilen
  komutlar için `low|medium|high` risk seviyesi içerir.
- Dashboard metrik grafikleri seçili zaman aralığıyla sorgulanır, ekrandaki
  metrikler CSV olarak dışa aktarılabilir ve log araması backend tarafında
  `q` parametresiyle yapılır.

## Veri Saklama

Backend periyodik bakım döngüsü eski kayıtları temizler:

- `METRIC_RETENTION_DAYS`
- `LOG_RETENTION_DAYS`
- `SERVICE_STATUS_RETENTION_DAYS`
- `AI_ANALYSIS_RETENTION_DAYS`

## Test ve Kalite

Backend:

```bash
cd backend
pytest
ruff check .
```

Agent:

```bash
cd agent
pytest
ruff check .
```

Dashboard:

```bash
cd dashboard
npm run lint
npm run build
```

## Güvenlik Notları

Production ortamında `SECRET_KEY` ve dashboard şifresi/hash'i güvenli değerlerle
tanımlanmalıdır. Production backend `DASHBOARD_PASSWORD_HASH` olmadan açılmaz.
Bu değer sha512-crypt veya bcrypt formatında elle yazılacaksa `.env` içinde tek
tırnakla saklanmalıdır; aksi halde Docker Compose hash içindeki `$` parçalarını
değişken interpolasyonu olarak yorumlayabilir.
Agent API anahtarları veritabanında hash'lenmiş saklanır; ham anahtar yalnızca
sunucu oluşturma veya anahtar yenileme yanıtında gösterilir.

Reverse proxy request body limitleri, HSTS ve temel security header'ları uygular.
Backend ayrıca metric/log ingestion şemalarında liste ve metin uzunluğu limitleri
tanımlar.

CI gate'leri backend testleri, agent testleri, dashboard lint/build,
`npm audit --omit=dev`, Python `pip-audit`, Docker build ve shellcheck içerir.
