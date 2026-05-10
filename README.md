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

## Agent Kurulumu

Dashboard'da yeni sunucu ekleyince tek kullanımlık API anahtarı ve kurulum komutu
üretilir. İzlenecek Linux sunucuda bu komutu root yetkisiyle çalıştırın.

Backend ayrıca kurulum için iki public dosya servis eder:

- `/install.sh`
- `/agent.tar.gz`

Agent varsayılan olarak 30 saniyede bir CPU, RAM, network, servis ve yeni logları;
60 saniyede bir disk ve process verilerini gönderir.

## Durum ve Alert Mantığı

- Sunucu ilk eklendiğinde `offline` olur.
- Agent metrik gönderince `online` olur ve `last_seen` güncellenir.
- Aktif alert varsa sunucu `warning` olarak görünür.
- `SERVER_OFFLINE_AFTER_SECONDS` boyunca heartbeat gelmezse sunucu `offline` olur.
- Alert'ler `dedupe_key` ile tekilleştirilir; warning alert critical seviyeye
  yükselirse mevcut alert güncellenir ve AI analiz tetiklenir.

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
