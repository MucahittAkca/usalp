# Usalp

AI destekli Linux sunucu izleme ve log analiz platformu.

## Mimari

- `backend`: FastAPI, PostgreSQL, Alembic, JWT auth, alert motoru ve AI analiz.
- `agent`: İzlenen Linux sunucuda çalışan metrik/log/servis toplayıcı.
- `dashboard`: Next.js dashboard.
- `nginx`: Dashboard ve API reverse proxy.

## Hızlı Kurulum

1. `.env.example` dosyasını `.env` olarak kopyalayın.
2. `POSTGRES_PASSWORD`, `SECRET_KEY`, `DASHBOARD_PASSWORD` veya
   `DASHBOARD_PASSWORD_HASH` değerlerini değiştirin.
3. Servisleri başlatın:

```bash
docker compose up --build
```

Geliştirme modunda hot reload için:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Dashboard: `http://localhost`

API dokümantasyonu development ortamında: `http://localhost/api/docs`

## Demo Modu

Örnek sunucular, metrik geçmişi, loglar, alert'ler ve AI analizleriyle çalışan
demo ortamını tek komutla başlatmak için:

```bash
./demo.sh
```

Dashboard: `http://localhost`

Demo kullanıcı bilgileri:

- Kullanıcı: `admin`
- Şifre: `admin`

Demo modu `DEMO_MODE=true` ile backend startup sırasında seed verisini üretir.
Varsayılan olarak yalnızca `usalp-demo-` API key prefix'li demo kayıtları
yenilenir; kullanıcı tarafından oluşturulan kayıtlar korunur. Demo verisini
her başlangıçta yenilememek için `DEMO_SEED_RESET=false` verilebilir.
Demo script'i varsayılan olarak `usalp_demo` Compose project adıyla ayrı volume
kullanır. Demo ortamını tamamen temizlemek için:

```bash
docker compose -p usalp_demo down -v
```

## Agent Kurulumu

Dashboard'da yeni sunucu ekleyince tek kullanımlık API anahtarı ve kurulum komutu
üretilir. İzlenecek Linux sunucuda bu komutu root yetkisiyle çalıştırın.

Backend ayrıca kurulum için iki public dosya servis eder:

- `/install.sh`
- `/agent.tar.gz`

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
tanımlanmalıdır. Agent API anahtarları dashboard üzerinden yenilenebilir veya
iptal edilebilir.
