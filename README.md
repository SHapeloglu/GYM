# GYM - Spor Salonu Yönetim Sistemi

Türkiye'de spor salonları için modern, açık kaynak gym yönetim yazılımı.
[wger](https://github.com/wger-project/wger) üzerine, ayrı bir `gym` Django
app'i olarak inşa edilmiştir.

![Status](https://img.shields.io/badge/Status-MVP%20Development-blue)
![License](https://img.shields.io/badge/License-AGPL%203.0-green)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![Django](https://img.shields.io/badge/Django-5.0-darkgreen)

## 🎯 Özellikler

### Sprint 1 — tamamlandı ve uçtan uca test edildi (14 Eylül 2026)
- ✅ Paket yönetimi (`/api/v2/gym/packages/`)
- ✅ Üyelik yönetimi (`/api/v2/gym/memberships/`)
- ✅ Ödeme kaydı — manuel/nakit (`/api/v2/gym/payments/`)
- ✅ Ders yönetimi (`/api/v2/gym/classes/`)
- ✅ Ders rezervasyonu + kapasite kontrolü (`/api/v2/gym/class-enrollment/`)
- ✅ Salon yönetim dashboard'u (`/api/v2/gym/dashboard/`)

Doğrulama süreci ve önceki rapordaki yanıltıcı maddeler için bkz.
[SPRINT1_VERIFICATION_REPORT.md](SPRINT1_VERIFICATION_REPORT.md).

### Sprint 2 — devam ediyor
- 🔄 iyzico ödeme entegrasyonu (SDK kuruldu, checkout/webhook yazılmadı)
- 🔄 Email bildirimleri (Celery)
- 🔄 İade (refund) akışı

Sprint 2'nin başındaki altyapı taşıma/cutover süreci için bkz.
[SPRINT2_INFRASTRUCTURE_MIGRATION.md](SPRINT2_INFRASTRUCTURE_MIGRATION.md).

### Planlanan (Faz 3+)
- ⬜ CRM & bildirim sistemi
- ⬜ KVKK & e-Fatura uyumu
- ⬜ Turnike/QR erişim kontrolü
- ⬜ Çoklu şube yönetimi
- ⬜ POS sistemi
- ⬜ Markalı mobil app
- ⬜ AI churn prediction

> **Not:** Bu listede yalnızca gerçekten çalıştığı doğrulanmış özellikler
> ✅ ile işaretlenir. Planlanan ama kodu yazılmamış hiçbir madde ✅
> almaz — Sprint 1'de bu hata yapıldığı için burada özellikle
> dikkat ediliyor.

## 🚀 Başlangıç

### Gereksinimler
- Docker & Docker Compose
- Python 3.12+ (container içinde)
- PostgreSQL 15 + Redis (compose ile geliyor)

### Kurulum

```bash
# Repo'yu klonla
git clone https://github.com/SHapeloglu/GYM.git
cd GYM/deploy

# Environment dosyasını düzenle (önce prod.env.example'dan kopyala)
cp config/prod.env.example config/prod.env
nano config/prod.env
# SECRET_KEY, POSTGRES_PASSWORD, SITE_URL'i güncelle

# web/celery_worker/celery_beat custom image kullanıyor (iyzipay için) — build şart
docker compose build

# Docker'ı başlat
docker compose up -d

# Migration'ları uygula
docker compose exec web python3 manage.py migrate

# Admin hesabı oluştur
docker compose exec web python3 manage.py createsuperuser

# wger fixture'larını yükle
docker compose exec web wger load-online-fixtures
```

> ⚠️ `docker compose build` adımı atlanamaz. `web`, `celery_worker` ve
> `celery_beat` servisleri `Dockerfile.gym` ile build edilir; resmi
> `wger/server:latest` image'ı doğrudan kullanılırsa `iyzipay` importu
> patlar. Ayrıntı: [INFRASTRUCTURE.md](INFRASTRUCTURE.md) §4.

### Erişim
- **Web:** http://gym.powerbi.com.tr:8090
- **Admin:** Giriş yaptıktan sonra dashboard

## 📁 Proje Yapısı
GYM/
├── deploy/ # Docker Compose konfigürasyonu (ana repo)
│ ├── config/ # nginx, env dosyaları
│ ├── services/ # Postgres, Redis include'ları
│ ├── Dockerfile.gym # web/celery için custom image (iyzipay)
│ └── docker-compose.yml
├── docker/ # wger-project/docker upstream (submodule, dokunulmaz)
├── custom-code/ # bind mount'lu kalıcı kaynak kod
│ ├── gym/ # gym app: models, serializers, views_api,
│ │ # urls_api, custom_urls, migrations, admin
│ └── main.py # Django ayarları + ROOT_URLCONF override
├── README.md
├── API.md # endpoint referansı
├── ARCHITECTURE.md # mimari + doğrulanmış DB şeması
├── INFRASTRUCTURE.md # kalıcılık stratejisi (ÖNCE BUNU OKUYUN)
├── SPRINT1_VERIFICATION_REPORT.md
└── SPRINT2_INFRASTRUCTURE_MIGRATION.md

> `docker/` klasörü **`wger-project/docker` upstream'inin submodule'ü**
> ve hiç değiştirilmez — kendi deployment config'imiz `deploy/` altında,
> ana repoya commit'lidir. Ayrıntı: SPRINT2_INFRASTRUCTURE_MIGRATION.md.

## 🛠️ Teknoloji Stack

| Bileşen | Teknoloji |
|---------|-----------|
| Backend | Django 5.0, DRF |
| Database | PostgreSQL 15 |
| Cache | Redis |
| Task Queue | Celery + Beat |
| Web Server | Nginx (port 8090) |
| Frontend | Vue.js (wger'dan miras) |
| Payment | iyzico — Sprint 2 |
| Deployment | Docker + Contabo (vmi3389964) |

## 🔐 Authentication

**DRF Token Authentication** kullanılıyor
(`wger.utils.timezone_auth.TimezoneTokenAuthentication`).

```bash
curl -H "Authorization: Token <token_key>" \
  https://gym.powerbi.com.tr/api/v2/gym/packages/
```

Token üretimi:
```python
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
token, _ = Token.objects.get_or_create(user=User.objects.get(username='...'))
print(token.key)
```

> ⚠️ Header `Bearer` değil **`Token`** ile başlar.
> `/api/v2/token/obtain/` diye bir endpoint **yoktur** — bu, Sprint 1'in
> ilk dokümantasyonundaki hatalı bir iddiaydı. JWT teorik olarak
> destekleniyor ama `allauth` headless OIDC akışı üzerinden yürüyor ve
> henüz kullanılmadı. Ayrıntı: [API.md](API.md).

## 🔒 Güvenlik

- CSRF token validation
- DRF Token authentication (JWT değil — yukarıya bakın)
- User isolation: kullanıcılar yalnızca kendi kayıtlarını görür, staff tümünü
- Dashboard yalnızca staff (`IsAdminUser`)
- Secret key ve DB şifresi `.gitignore`'lı `prod.env`'de, git'e girmez
- HTTPS ready
- ⬜ KVKK uyumu (veri silme) — Faz 3
- ⬜ Rate limiting (Django Axes) — planlanan

## 📖 Dokümantasyon

| Doküman | İçerik |
|---|---|
| [INFRASTRUCTURE.md](INFRASTRUCTURE.md) | Kalıcılık stratejisi, bind mount'lar, Dockerfile — **kod yazmadan önce okuyun** |
| [API.md](API.md) | 6 endpoint, auth, request/response örnekleri, error response'lar |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Mimari katmanlar, doğrulanmış DB şeması, Sprint 2 taslağı |
| [SPRINT1_VERIFICATION_REPORT.md](SPRINT1_VERIFICATION_REPORT.md) | 13-14 Eylül doğrulama bulguları |
| [SPRINT2_INFRASTRUCTURE_MIGRATION.md](SPRINT2_INFRASTRUCTURE_MIGRATION.md) | 16-18 Eylül altyapı taşıma/cutover kaydı |

## ⚙️ Geliştirme Kuralları

1. `gym/` app kodu host'ta `custom-code/gym/` altında ve bind mount'lu —
   `docker exec` ile yapılan düzenlemeler otomatik host'a yazılır.
2. Yeni Python paketi eklerken **asla** `docker compose exec web pip install`
   kullanmayın. `deploy/Dockerfile.gym`'e `RUN pip install ...` ekleyip
   `docker compose build` çalıştırın.
3. `wger/urls.py` **hiç değiştirilmez** — route'lar
   `wger/gym/custom_urls.py` üzerinden `ROOT_URLCONF` override ile eklenir.
4. Bind mount edilmeyen hiçbir dosya kalıcı değildir.
5. `docker/` submodule'üne asla doğrudan değişiklik commit etmeyin —
   deployment config değişiklikleri `deploy/` altına gider.
6. Birden fazla stack kopyası aynı host'ta çalışacaksa, her kopyanın
   `docker-compose.yml`'inde `networks.default.name` benzersiz olmalı.

Gerekçeler ve ayrıntı: [INFRASTRUCTURE.md](INFRASTRUCTURE.md) ve
[SPRINT2_INFRASTRUCTURE_MIGRATION.md](SPRINT2_INFRASTRUCTURE_MIGRATION.md).

## 📊 Roadmap

| Faz | Hedef | Bitiş |
|-----|-------|-------|
| 1 | MVP (Üyelik + Ödeme + Ders) | 2026-10-24 |
| 2 | Dashboard + CRM | 2026-11-07 |
| 3 | KVKK + e-Fatura | 2026-11-30 |
| 4 | Turnike/QR Erişim | 2026-12-31 |
| 5 | Markalı App | 2027-01-31 |

## 🤝 Katkı

1. Fork et
2. Feature branch oluştur (`git checkout -b feature/amazing-feature`)
3. Commit et (`git commit -m 'Add amazing feature'`)
4. Push et (`git push origin feature/amazing-feature`)
5. Pull Request aç

## 📄 Lisans

AGPL 3.0 - [LICENSE](LICENSE) dosyasını gör

**Not:** MVP'den sonra MIT'ye geçiş planlandı (kapalı kaynak SaaS için)

## 👨‍💼 İletişim

- **Proje Sahibi:** Selim Kılıç
- **Email:** selim.kilic@olap.com.tr
- **GitHub:** [@SHapeloglu](https://github.com/SHapeloglu)

## 🎯 MVP Lansmanı

**Hedef:** 2026-11-30
**İlk Müşteri:** 2026-12-15

---

**Geliştirme Başlangıcı:** 2026-09-09
**Son Güncelleme:** 2026-09-18 (Sprint 2 altyapı cutover sonrası)
