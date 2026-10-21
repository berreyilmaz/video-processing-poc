
# Video Processing PoC

Video dosyalarının yüklenmesini, arka planda işlenmesini, sonuçların depolanmasını ve işlem durumlarının takip edilmesini sağlayan bir Proof of Concept (PoC) projesidir.

Proje; FastAPI, MongoDB, MinIO, OpenCV ve Docker Compose kullanılarak geliştirilmiştir.

## 1. Kullanılan Teknolojiler

- Python
- FastAPI
- MongoDB
- MinIO
- OpenCV
- Docker
- Docker Compose

## 2. Sistem Mimarisi

Proje dört temel servisten oluşur:

- **API:** Video yükleme ve iş durumu sorgulama işlemlerini yönetir.
- **Worker:** Videoları arka planda işler ve sonuçları oluşturur.
- **MongoDB:** İş kayıtlarını ve özet metrikleri saklar.
- **MinIO:** Video dosyalarını ve işlem sonuçlarını depolar.

### İş Akışı

1. Kullanıcı video dosyasını API üzerinden yükler.
2. Video MinIO üzerinde saklanır.
3. MongoDB üzerinde bir iş kaydı oluşturulur.
4. Worker bekleyen işi alır ve videoyu işler.
5. İşleme sonuçları JSONL dosyası olarak MinIO'ya kaydedilir.
6. İş durumu ve özet metrikler MongoDB'ye yazılır.
7. Kullanıcı iş durumunu ve metrikleri API üzerinden sorgular.

> **Not:** Mevcut PoC sürümünde oyuncu koordinatları sentetik olarak üretilir. Gerçek bir yapay zekâ tabanlı oyuncu tespit modeli kullanılmamaktadır.

## 3. Gereksinimler

Projeyi çalıştırmadan önce aşağıdaki araçların kurulu olması gerekir:

- Docker Desktop
- Git

Kurulumları kontrol etmek için terminalde şu komutları çalıştırın:

```bash
docker --version
docker compose version
git --version
```

## 4. Projenin Kurulumu

### Adım 1: Projeyi indirin

GitHub deposundan projeyi klonlayın:

```bash
git clone <REPOSITORY_URL>
cd video-processing-poc
```

`<REPOSITORY_URL>` yerine kendi GitHub depo adresinizi yazın.

Depoyu daha önce indirdiyseniz doğrudan proje klasörüne geçebilirsiniz.

### Adım 2: Ortam değişkenlerini hazırlayın

Proje kök dizininde `.env.example` dosyası bulunuyorsa aşağıdaki komutu çalıştırın:

```bash
cp .env.example .env
```

Ardından `.env` dosyasını açarak MongoDB ve MinIO bağlantı bilgilerini kontrol edin.

> Güvenlik için `.env` dosyasını GitHub'a yüklemeyin. Gerçek kullanıcı adı, parola ve erişim anahtarlarını herkese açık şekilde paylaşmayın.

### Adım 3: Docker servislerini başlatın

Proje kök dizininde şu komutu çalıştırın:

```bash
docker compose up --build
```

Bu komut gerekli Docker imajlarını oluşturur ve MongoDB, MinIO, API ve Worker servislerini başlatır.

Servisleri arka planda çalıştırmak için:

```bash
docker compose up --build -d
```

### Adım 4: Servislerin durumunu kontrol edin

```bash
docker compose ps
```

Çalışan servislerin durumlarını bu komutla görebilirsiniz.

API veya Worker loglarını incelemek için:

```bash
docker compose logs -f api
```

```bash
docker compose logs -f worker
```

Tüm servislerin loglarını görüntülemek için:

```bash
docker compose logs -f
```

## 5. Uygulamaya Erişim

Servisler başlatıldıktan sonra aşağıdaki adresleri kullanabilirsiniz:

| Servis | Adres | Açıklama |
|---|---|---|
| Swagger UI | http://127.0.0.1:8000/docs | API endpoint'lerini test etme |
| API Health Check | http://127.0.0.1:8000/health | API sağlık kontrolü |
| MinIO Console | http://localhost:9001 | Dosya depolama arayüzü |

MinIO Console giriş bilgileri `.env` dosyasında tanımlıdır.

## 6. Video Yükleme ve Test

### Adım 1: Swagger arayüzünü açın

Tarayıcıda aşağıdaki adresi açın:

http://127.0.0.1:8000/docs

### Adım 2: Video yükleyin

1. `POST /videos` endpoint'ini açın.
2. **Try it out** butonuna tıklayın.
3. Bir video dosyası seçin.
4. **Execute** butonuna basın.
5. Yanıtta dönen `job_id` değerini kopyalayın.

Desteklenen video uzantıları:

- `.mp4`
- `.mov`
- `.avi`
- `.mkv`

### Adım 3: İş durumunu kontrol edin

`GET /jobs/{job_id}` endpoint'ini açın.

1. Video yükleme yanıtından aldığınız `job_id` değerini girin.
2. **Execute** butonuna tıklayın.
3. İşin güncel durumunu kontrol edin.

### Adım 4: İşleme metriklerini alın

İş durumu `completed` olduğunda `GET /jobs/{job_id}/metrics` endpoint'ini çağırın.

Bu endpoint, tamamlanan işin özet metriklerini döndürür.

## 7. API Endpoint'leri

| Method | Endpoint | Açıklama |
|---|---|---|
| GET | `/` | API'nin temel yanıtı |
| GET | `/health` | Sağlık kontrolü |
| POST | `/videos` | Video yükler ve iş kaydı oluşturur |
| GET | `/jobs/{job_id}` | İş durumunu ve hata bilgilerini getirir |
| GET | `/jobs/{job_id}/metrics` | Tamamlanan işin metriklerini getirir |

## 8. İş Durumları

| Durum | Açıklama |
|---|---|
| `pending` | İşlenmeyi bekliyor |
| `processing` | Worker tarafından işleniyor |
| `completed` | İşlem başarıyla tamamlandı |
| `failed` | İşlem başarısız oldu |

Worker, işleme sırasında hata oluşması durumunda sınırlı sayıda yeniden deneme yapabilir. Süresi dolan işlerin yeniden alınması için lease mekanizması kullanılır.

## 9. Sık Karşılaşılan Sorunlar

### API açılmıyorsa

```bash
docker compose ps
docker compose logs -f api
```

API servisinin durumunu ve hata kayıtlarını kontrol edin.

### Worker işlem yapmıyorsa

```bash
docker compose logs -f worker
```

Worker loglarından işin alınıp alınmadığını ve işleme sırasında hata oluşup oluşmadığını inceleyin.

### MinIO bağlantı hatası oluşuyorsa

Docker Compose içerisindeki servisler arası bağlantıda doğru servis adının kullanıldığını kontrol edin. Örneğin MinIO adresi, konteynerler arasındaki bağlantıda `minio:9000` olabilir.

Ayrıca `.env` dosyasındaki bağlantı ayarlarını kontrol edin.

### Konteynerleri yeniden başlatmak gerekiyorsa

```bash
docker compose restart
```

## 10. Servisleri Durdurma

Arka planda çalışan servisleri durdurmak için:

```bash
docker compose down
```

Verileri içeren Docker volume'larını da silmek için:

```bash
docker compose down -v
```

> **Dikkat:** `docker compose down -v` komutu kalıcı depolama verilerini silebilir. Yalnızca bu verileri kaybetmeyi kabul ediyorsanız kullanın.

## 11. Gelecek Geliştirmeler

- Gerçek oyuncu tespit ve takip modeli entegrasyonu
- Gerçek GPU üzerinde performans benchmark'ı
- Görsel Dashboard geliştirilmesi
- Otomatik hata kurtarma ve yeniden kuyruğa alma
- Kimlik doğrulama ve yetkilendirme
- Üretim ortamına uygun güvenlik ve izleme yapılandırmaları

## 12. Güvenlik Notları

- `.env` dosyasını GitHub'a yüklemeyin.
- Gerçek parolaları ve erişim anahtarlarını herkese açık ortamlarda paylaşmayın.
- Üretim ortamında güçlü kimlik bilgileri kullanın.
- Daha önce açığa çıkmış gerçek parolaları ve erişim anahtarlarını değiştirin.
