# Usalp: AI Destekli Linux Sunucu İzleme ve Log Analiz Platformu

## Bitirme Projesi Raporu

**Proje Adı:** Usalp
**Proje Türü:** Web tabanlı Linux sunucu izleme ve analiz sistemi
**Teslim Ortamı:** GitHub deposu ve tek komutla çalışan demo ortamı
**Demo Adresi:** `http://localhost`
**Demo Kullanıcı Bilgileri:** `admin / admin`
**Demo Çalıştırma Komutu:** `./demo.sh`
**Tarih:** Haziran 2026

> Not: Bu raporda herhangi bir gizli API anahtarı, gerçek şifre veya `.env` içeriği yer almaz. Gerçek LLM/API anahtarları güvenlik sebebiyle rapora ve GitHub deposuna eklenmemiştir.

---

## 1. Özet

Usalp, Linux sunucuların merkezi bir panel üzerinden izlenmesini, metriklerin toplanmasını, servis durumlarının takip edilmesini, log kayıtlarının incelenmesini ve alarm durumlarının analiz edilmesini sağlayan bir bitirme projesidir. Sistem; FastAPI tabanlı backend, Next.js tabanlı dashboard, PostgreSQL veritabanı, Caddy reverse proxy ve Linux üzerinde çalışan agent bileşenlerinden oluşur.

Projenin temel amacı, birden fazla Linux sunucudan gelen CPU, RAM, disk, ağ, servis ve log verilerini tek bir arayüzde toplamak; eşik değerleri aşıldığında alarm üretmek; bu alarmları kullanıcıya anlamlı şekilde göstermek ve uygun koşullarda AI destekli kök neden analizi sunmaktır.

Demo ortamında gerçek sunuculara bağlanma zorunluluğu olmadan sistemi gösterebilmek için deterministik örnek veriler üretilmiştir. Dashboard'da görünen `[DEMO]` etiketli AI analizleri gerçek LLM çağrısı sonucu değildir; proje sunumunda AI analiz ekranının boş kalmaması ve beklenen iş akışının gösterilebilmesi için önceden seed edilen örnek analiz kayıtlarıdır. Gerçek AI analizi desteği uygulama içinde mevcuttur; ancak bunun çalışması için kullanıcının kendi `LLM_API_KEY` değerini yerel `.env` dosyasına eklemesi gerekir.

---

## 2. Problem Tanımı

Linux sunucuların izlenmesi, servislerin ayakta tutulması ve hata durumlarının hızlı tespit edilmesi sistem yönetimi için kritik bir konudur. Geleneksel yaklaşımda sistem yöneticisi farklı makinelere terminal üzerinden bağlanarak metrik, servis ve log durumlarını manuel kontrol eder. Bu yöntem:

- Zaman alıcıdır.
- Birden fazla sunucu olduğunda takibi zorlaştırır.
- Log ve metrik korelasyonunu manuel hale getirir.
- Kritik alarm durumlarında geç tepki verilmesine sebep olabilir.
- Yeni başlayan kullanıcılar için hata nedenini yorumlamayı zorlaştırır.

Usalp bu problemi merkezi, web tabanlı, kolay çalışan ve AI destekli bir izleme platformu ile çözmeyi hedefler.

---

## 3. Projenin Amacı ve Hedefleri

Projenin ana hedefleri şunlardır:

1. Linux sunuculardan periyodik olarak metrik toplamak.
2. CPU, RAM, disk, ağ, servis ve log verilerini merkezi backend'e göndermek.
3. Verileri PostgreSQL üzerinde kalıcı olarak saklamak.
4. Kullanıcıya modern bir dashboard üzerinden sunucu durumlarını göstermek.
5. Eşik aşımı veya servis hatası durumunda alarm üretmek.
6. Alarm ve log verilerinden anlamlı analiz üretebilecek AI altyapısını sağlamak.
7. Güvenlik nedeniyle gizli anahtarları GitHub deposuna dahil etmemek.
8. Üniversite demosu için sistemi tek komutla çalışır hale getirmek.

---

## 4. Kullanılan Teknolojiler

| Bileşen | Teknoloji | Açıklama |
| --- | --- | --- |
| Backend | FastAPI | REST API, kimlik doğrulama, metrik alımı, alarm ve AI servisleri |
| Veritabanı | PostgreSQL | Sunucu, metrik, log, servis, alarm ve analiz verilerinin saklanması |
| ORM/Migration | SQLAlchemy, Alembic | Veritabanı modelleri ve migration yönetimi |
| Dashboard | Next.js, React, TypeScript | Web arayüzü |
| Stil | Tailwind CSS | Dashboard arayüz tasarımı |
| Reverse Proxy | Caddy | Dashboard ve API'yi tek origin altında yayınlama |
| Container | Docker Compose | Demo ve production benzeri çalışma ortamı |
| Agent | Python | Linux sistemlerden veri toplayan istemci |
| AI/LLM | OpenRouter uyumlu LLM API | Opsiyonel gerçek AI analizi |

---

## 5. Sistem Mimarisi

Usalp beş ana bileşenden oluşur:

```text
Linux Sunucu
   |
   |  Agent metrik/log/servis verisi gönderir
   v
Backend API (FastAPI)
   |
   |  Verileri kaydeder, alarm üretir, AI analiz tetikler
   v
PostgreSQL
   ^
   |
Dashboard (Next.js) <--- Caddy Reverse Proxy ---> Kullanıcı
```

### 5.1 Backend

Backend, sistemin ana iş mantığını yürüten FastAPI uygulamasıdır. Başlıca görevleri:

- Dashboard kullanıcısı için JWT tabanlı kimlik doğrulama.
- Agent API anahtarı doğrulama.
- Sunucu kaydı oluşturma ve API key döndürme.
- Metrik, servis ve log verilerini alma.
- Alarm motorunu çalıştırma.
- AI analiz kayıtlarını oluşturma.
- Demo verisini startup sırasında seed etme.
- Eski veriler için retention/bakım işlemleri.

### 5.2 Dashboard

Dashboard, kullanıcının sistemi yönettiği web arayüzüdür. Başlıca ekranlar:

- Genel bakış.
- Sunucu listesi.
- Sunucu detay sayfası.
- Metrik grafikleri.
- Servis durum listesi.
- Log görüntüleme.
- Alarm merkezi.
- AI analiz paneli.

Sunucu kartları performans için optimize edilmiştir. Kartlar artık her sunucu için ayrı ayrı metrik ve alarm isteği atmak yerine backend'in liste yanıtında döndürdüğü özet alanları kullanır.

### 5.3 Agent

Agent, izlenecek Linux sunucuda çalışan Python tabanlı istemcidir. CPU, RAM, disk, ağ, servis ve log verilerini toplar. Verileri backend'e göndermeden önce lokal kuyruğa alarak geçici ağ problemlerinde veri kaybını azaltır.

### 5.4 Caddy

Caddy, dashboard ve backend API'yi aynı origin altında yayınlayan reverse proxy bileşenidir. Demo ortamında `http://localhost` üzerinden çalışır. Production ortamında gerçek domain ve ACME e-posta bilgisiyle otomatik HTTPS desteği kullanılabilir.

### 5.5 PostgreSQL

PostgreSQL, sistemin kalıcı veri katmanıdır. Sunucular, metrikler, servis durumları, loglar, alarmlar ve AI analiz kayıtları burada saklanır.

---

## 6. Temel Özellikler

### 6.1 Sunucu Yönetimi

Kullanıcı dashboard üzerinden yeni sunucu ekleyebilir. Sistem, agent kurulumu için tek kullanımlık bir API anahtarı üretir. Bu ham anahtar yalnızca oluşturma veya anahtar yenileme anında gösterilir; daha sonra sistemden geri okunamaz.

### 6.2 Metrik Toplama

Agent aşağıdaki verileri toplar:

- CPU kullanımı
- RAM kullanımı
- Disk kullanımı
- Ağ giriş/çıkış değerleri
- Load average
- Servis durumları
- Log satırları

Dashboard tarafında metrikler grafik ve kart özetleri halinde gösterilir.

### 6.3 Alarm Üretimi

Backend alarm motoru, belirlenen eşik değerleri aşıldığında alarm oluşturur. Örnek alarm tipleri:

- CPU eşik aşımı
- RAM eşik aşımı
- Disk eşik aşımı
- Servis hatası
- Kritik log yoğunluğu

Alarm kayıtları `dedupe_key` mantığı ile tekilleştirilir. Böylece aynı problem için sürekli yeni alarm üretilmesi engellenir.

### 6.4 AI Analiz Altyapısı

Sistem, alarm ve log verileri üzerinden AI destekli analiz üretmek için tasarlanmıştır. Analiz sonucunda:

- Özet
- Muhtemel nedenler
- Kanıt satırları
- Önerilen komutlar
- Risk seviyesi
- Güven skoru

gibi bilgiler saklanabilir.

---

## 7. Demo Ortamı ve Sahte AI Analizi Açıklaması

Üniversite sunumunda sistemin gerçek sunuculara, gerçek alarmlara ve ücretli/harici LLM servisine bağımlı olmadan gösterilebilmesi için demo modu eklenmiştir.

Demo modu `./demo.sh` komutu ile başlatılır. Bu komut:

- Docker Compose projesini `usalp_demo` adı ile çalıştırır.
- Eski orphan container'ları temizler.
- PostgreSQL, backend, dashboard ve Caddy servislerini ayağa kaldırır.
- Backend startup sırasında örnek demo verilerini oluşturur.
- `http://localhost` adresinden dashboard'u yayınlar.

Demo verileri şunları içerir:

- Örnek production, staging ve development sunucuları.
- CPU, RAM, disk ve ağ metrik geçmişi.
- Servis durumları.
- Log kayıtları.
- Aktif ve çözülmüş alarm kayıtları.
- `[DEMO]` etiketli örnek AI analizleri.

### 7.1 Sahte AI Analizi Neden Var?

Dashboard'daki AI analiz ekranının sunum sırasında boş kalmaması için demo verisiyle uyumlu örnek analiz kayıtları seed edilmiştir. Bu kayıtlar gerçek LLM çağrısı sonucu üretilmiş gibi gösterilmez; özetlerinde açık şekilde `[DEMO]` etiketi bulunur.

Bu tercih bilinçli olarak yapılmıştır:

- Üniversite demosunun internet/API key bağımlılığını azaltır.
- Harici LLM servis maliyeti oluşturmaz.
- API key paylaşmadan AI analiz ekranının iş akışı gösterilebilir.
- Değerlendirme sırasında her çalıştırmada tutarlı veri görünmesini sağlar.

Gerçek AI analizi kod tabanında mevcuttur. `LLM_API_KEY` tanımlıysa dashboard'daki "Yeni Analiz Başlat" akışı gerçek LLM servisine istek gönderir. Key tanımlı değilse sistem çalışmaya devam eder ve manuel AI analiz çağrısı sonucunda analiz üretilmez.

---

## 8. API Key ve Güvenlik Durumu

Bu projede iki farklı API key/secret konusu vardır:

1. **LLM API Key:** OpenRouter/LLM servisi için kullanılan harici servis anahtarı.
2. **Agent API Key:** Linux agent'in backend'e veri gönderirken kullandığı anahtar.

### 8.1 LLM API Key Neden Eklenmedi?

Gerçek LLM API key değeri güvenlik sebebiyle GitHub deposuna, rapora veya demo çıktısına eklenmemiştir. Bu anahtar eklenirse:

- Yetkisiz kişiler tarafından kullanılabilir.
- Ücretli API kotası tüketilebilir.
- Servis hesabı ele geçirilebilir.
- GitHub geçmişinden tamamen temizlenmesi zor olabilir.

Bu nedenle projede yalnızca örnek kullanım belirtilmiştir:

```bash
LLM_API_KEY=sk-or-v1-...
```

Gerçek değer kullanıcının kendi bilgisayarında, GitHub'a eklenmeyen `.env` dosyasına yazılmalıdır.

### 8.2 `.env` Dosyası Neden Commitlenmez?

`.env` dosyası veritabanı şifresi, JWT secret, dashboard şifresi/hash'i, LLM API key ve bildirim kanalı bilgileri gibi hassas değerler içerebilir. Bu nedenle `.gitignore` içinde `.env`, `.env.local` ve `.env.*.local` dosyaları hariç tutulmuştur.

Depoda `.env.example` bulunabilir; ancak bu dosya gerçek sırlar yerine örnek/değer bekleyen alanlar içermelidir.

### 8.3 Agent API Key Güvenliği

Agent API anahtarları ham haliyle veritabanında saklanmaz. Anahtarlar SHA-256 tabanlı tek yönlü özet formatına çevrilir ve `sha256:` prefix'i ile saklanır. Ham anahtar yalnızca:

- Sunucu oluşturma yanıtında
- Anahtar yenileme yanıtında

bir kez gösterilir. Daha sonra tekrar görüntülenemez. Bu yaklaşım, veritabanı ele geçse bile ham agent anahtarlarının doğrudan okunmasını engeller.

### 8.4 Dashboard Kimlik Doğrulama

Dashboard kullanıcısı JWT tabanlı oturum ile doğrulanır. Demo ortamında kolay kullanım için `admin/admin` bilgileri vardır. Production ortamında güçlü secret, güçlü şifre ve hash kullanımı zorunlu tutulmuştur.

---

## 9. Demo Verisinin Deterministik Olması

Demo ortamında verilerin her sayfa yenilemede veya backend restart'ında rastgele değişmemesi önemlidir. Bu nedenle demo seed mekanizması aşağıdaki kurallara göre tasarlanmıştır:

- Yalnızca `.usalp.demo` hostname suffix'li demo kayıtları resetlenir.
- Kullanıcı tarafından eklenen manuel sunucu kayıtları korunur.
- Demo server kayıtlarının ID değerleri restart sonrasında korunur.
- Demo child verileri, yani metrik/log/servis/alarm/analiz kayıtları yeniden oluşturulabilir.
- Demo sunucular stale maintenance işleminde rastgele offline'a düşürülmez.
- `[DEMO]` AI analizleri her demo başlangıcında tekrar hazır edilir.

Bu sayede sunum sırasında F5 atmak veya backend'i yeniden başlatmak demo akışını bozmaz.

---

## 10. Kurulum ve Çalıştırma

### 10.1 Demo Modu

Demo ortamını başlatmak için:

```bash
./demo.sh
```

Çalıştıktan sonra:

- Dashboard: `http://localhost`
- Kullanıcı adı: `admin`
- Şifre: `admin`

Demo ortamını durdurmak için:

```bash
docker compose -p usalp_demo down
```

Demo verisini tamamen silmek ve volume'leri temizlemek için:

```bash
docker compose -p usalp_demo down -v
```

### 10.2 Production Kurulum

Production kurulum için merkezi kontrol düzlemi sunucusunda public DNS kaydı,
80/443 portlarının açık olması, Docker Compose v2, `git`, `curl` ve `openssl`
gerekir. Boş bir Ubuntu sunucuda ön hazırlık:

```bash
apt update
apt install -y git curl openssl docker.io docker-compose-plugin
systemctl enable --now docker
docker compose version
```

Kalıcı production ortamında gerçek domain kullanılması önerilir. Geçici test
veya sunum ortamında domain henüz hazır değilse public IP'yi çözen
`IP.sslip.io` formatı kullanılabilir.

Uygulama kurulumu:

```bash
git clone https://github.com/MucahittAkca/usalp.git /opt/usalp
cd /opt/usalp
./scripts/setup-prod.sh
```

Bu script `.env` dosyası oluşturur, secret değerleri hazırlar, dashboard
şifresini hash'ler, DNS/port/outbound HTTPS kontrollerini yapar ve Docker
Compose ile sistemi ayağa kaldırır.

Kurulum sonrası browser login 401 dönüyorsa backend erişilebilir durumdadır,
ancak browser'dan gönderilen kullanıcı adı/şifre kurulumdaki değerlerle
eşleşmiyordur. Dashboard şifresi tek komutla sıfırlanıp backend üzerinden
doğrulanabilir:

```bash
./scripts/setup-prod.sh --reset-dashboard-password
```

Gerçek AI analizi için production sunucusundaki `.env` dosyasına
`LLM_API_KEY` eklenir ve backend yeniden oluşturulur:

```bash
LLM_API_KEY=sk-or-v1-...
docker compose up -d --force-recreate backend
```

### 10.3 Agent Kurulumu

Agent, izlenecek Linux sunucuda çalışır ve merkezi backend'e HTTPS üzerinden
veri gönderir. Agent sunucusunda systemd, outbound HTTPS erişimi, Python 3.12+,
`python3-venv`, `curl` ve `tar` gerekir. Boş bir Ubuntu sunucuda:

```bash
apt update
apt install -y curl tar python3 python3-venv
```

Dashboard'da yeni sunucu eklendiğinde tek kullanımlık agent API anahtarı ve
kurulum komutu üretilir. Komut genel olarak şu formdadır:

```bash
curl -fsSL https://domain/install.sh | sudo bash -s -- --api-key <key> --backend-url https://domain
```

Kurulumdan sonra agent servis durumu ve logları şu komutlarla kontrol edilir:

```bash
systemctl status usalp-agent --no-pager
journalctl -u usalp-agent -n 50 --no-pager
```

Agent dosyaları `/opt/usalp-agent`, yapılandırma dosyası
`/etc/usalp-agent/agent.yaml`, kalıcı kuyruk verileri
`/var/lib/usalp-agent/queue` altında tutulur.

---

## 11. Test ve Doğrulama

Projede backend, dashboard, shell script ve Docker/Caddy yapılandırmaları test edilmiştir.

Çalıştırılan başlıca kontroller:

```bash
timeout 180 backend/.venv/bin/pytest backend/tests
backend/.venv/bin/ruff check backend/app backend/tests
(cd agent && pytest)
(cd dashboard && npm run lint)
(cd dashboard && npm run build)
bash -n demo.sh scripts/setup-prod.sh
docker compose config --quiet
caddy validate --config /etc/caddy/Caddyfile
```

Canlı demo ortamında doğrulanan endpoint ve route'lar:

- `GET /health`
- `POST /api/v1/auth/token`
- `GET /api/v1/servers`
- `GET /api/v1/servers/{id}`
- `GET /api/v1/servers/{id}/metrics`
- `/servers`
- `/servers/1`
- `/servers/{id}`
- `/servers/{id}#services`
- `/servers/{id}#logs`
- `/servers/{id}#ai`

Son test sonucunda backend test paketinde `199 passed` sonucu alınmıştır.

---

## 12. Karşılaşılan Sorunlar ve Çözümler

| Sorun | Çözüm |
| --- | --- |
| Demo verileri restart sonrası değişebiliyordu | Demo seed deterministik hale getirildi |
| Demo sunucular stale job ile offline olabiliyordu | `.usalp.demo` kayıtları stale offline işleminden muaf tutuldu |
| Kart başına fazla API isteği atılıyordu | Server liste endpoint'i kart özetleri döndürecek şekilde genişletildi |
| Eski container port 80'i tutabiliyordu | `demo.sh` içine `down --remove-orphans` eklendi |
| Caddy boş ACME email durumunda hata verebiliyordu | Demo için güvenli default email değeri tanımlandı |
| Gerçek LLM key depoya eklenemezdi | LLM key opsiyonel yapıldı, demo için `[DEMO]` analizleri seed edildi |
| Boş VPS üzerinde Docker kurulu değildi | README ve rapora Docker Compose v2 ön hazırlık komutları eklendi |
| Agent installer pipe ile çalışırken script yolunu okuyamıyordu | Installer `curl ... \| bash` kullanımına uyumlu hale getirildi |
| Yeni `structlog` sürümünde agent başlangıçta hata veriyordu | Log seviyesi okuma kodu `structlog` iç API'sine bağımlı olmayacak şekilde güncellendi |

---

## 13. Sınırlamalar

Proje çalışır ve demo için hazır durumdadır; ancak aşağıdaki sınırlamalar vardır:

- Gerçek AI analizi için kullanıcının kendi LLM API key'ini sağlaması gerekir.
- Demo ortamındaki `[DEMO]` analizler gerçek LLM çağrısı değildir.
- Kalıcı production kurulumu için gerçek domain, açık 80/443 portları ve güvenli `.env` gereklidir; geçici testte `IP.sslip.io` formatı kullanılabilir.
- Demo kullanıcı bilgileri kolay sunum için basittir; production'da kullanılmamalıdır.
- Üniversite demosunda internet bağlantısı yoksa harici LLM analizi çalışmaz; ancak demo verisi ve panel çalışmaya devam eder.

---

## 14. Gelecek Geliştirmeler

Proje ileride şu şekillerde geliştirilebilir:

- Çok kullanıcılı rol bazlı yetkilendirme.
- Daha gelişmiş alarm kuralları ve eşik yönetimi.
- Telegram, Slack ve e-posta bildirimlerinin dashboard üzerinden yönetilmesi.
- Agent otomatik güncelleme mekanizması.
- Daha detaylı process analizi.
- AI analizlerinde geçmiş olaylarla karşılaştırma.
- Kubernetes veya container monitoring desteği.
- Dashboard üzerinden rapor dışarı aktarma.

---

## 15. Sonuç

Usalp, Linux sunucuların merkezi olarak izlenmesi, metrik ve log verilerinin toplanması, alarm üretilmesi ve AI destekli analiz altyapısının kurulması hedeflerini karşılayan çalışır bir bitirme projesidir.

Proje, üniversite demosu için tek komutla çalışacak şekilde hazırlanmıştır. Demo ortamında gerçek LLM API key gerektirmeden sistemin tüm ana ekranları ve analiz akışı gösterilebilir. Bunun için `[DEMO]` etiketli örnek AI analizleri bilinçli olarak seed edilmiştir. Gerçek LLM entegrasyonu ise güvenlik gereği depoya eklenmeyen `LLM_API_KEY` değeri kullanıcı tarafından sağlandığında devreye girer.

Güvenlik açısından `.env` dosyası GitHub'a dahil edilmemiş, agent API anahtarları hash'lenmiş, production ortamında güvenli secret ve şifre/hash kullanımı zorunlu tutulmuştur. Bu yönleriyle proje hem demo hem de production'a yakın bir mimariyi gösterebilecek olgunluğa getirilmiştir.
