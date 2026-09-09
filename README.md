# GYM - Spor Salonu Yönetim Sistemi

Türkiye'de spor salonları için modern, açık kaynak gym yönetim yazılımı.

![Status](https://img.shields.io/badge/Status-MVP%20Development-blue)
![License](https://img.shields.io/badge/License-AGPL%203.0-green)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![Django](https://img.shields.io/badge/Django-4.2-darkgreen)

## 🎯 Özellikler

### MVP (Faz 1-3)
- ✅ Üyelik/Paket Yönetimi
- ✅ iyzico Ödeme Entegrasyonu
- ✅ Ders/Sınıf Rezervasyonu
- ✅ Salon Yönetim Dashboard
- ✅ CRM & Bildirim Sistemi
- ✅ KVKK & e-Fatura Uyumu

### Gelecek (Faz 4+)
- 🔄 Turnike/QR Erişim Kontrolü
- 🔄 Çoklu Şube Yönetimi
- 🔄 POS Sistemi
- 🔄 Markalı Mobil App
- 🔄 AI Churn Prediction

## 🚀 Başlangıç

### Gereksinimler
- Docker & Docker Compose
- PostgreSQL 15+
- Redis
- Python 3.12+

### Kurulum

```bash
# Repo'yu klonla
git clone https://github.com/SHapeloglu/GYM.git
cd GYM/docker

# Environment dosyasını düzenle
nano config/prod.env
# SECRET_KEY ve SITE_URL'i güncelle

# Docker'ı başlat
docker compose up -d

# Admin hesabı oluştur
docker compose exec web python3 manage.py createsuperuser

# Verileri yükle
docker compose exec web python3 manage.py migrate
docker compose exec web wger load-online-fixtures
```

### Erişim
- **Web:** http://gym.powerbi.com.tr:8090
- **Admin:** Giriş yaptıktan sonra dashboard

## 📁 Proje Yapısı
GYM/
├── docker/ # Docker Compose konfigürasyonu
│ ├── config/ # nginx, env dosyaları
│ ├── services/ # Postgres, Redis
│ └── docker-compose.yml
├── docs/ # Dokümantasyon
│ ├── architecture.md # Sistem mimarisi
│ ├── backlog.md # Product backlog
│ └── task.md # Sprint görevleri
├── wger/ # wger fork (antrenman modülü)
└── README.md

## 🛠️ Teknoloji Stack

| Bileşen | Teknoloji |
|---------|-----------|
| Backend | Django 4.2, DRF |
| Database | PostgreSQL 15 |
| Cache | Redis |
| Task Queue | Celery + Beat |
| Web Server | Nginx |
| Frontend | Vue.js (wger) |
| Payment | iyzico (Türkiye) |
| Deployment | Docker + Contabo |

## 📊 Roadmap

| Faz | Hedef | Bitiş |
|-----|-------|-------|
| 1 | MVP (Üyelik + Ödeme + Ders) | 2026-10-24 |
| 2 | Dashboard + CRM | 2026-11-07 |
| 3 | KVKK + e-Fatura | 2026-11-30 |
| 4 | Turnike/QR Erişim | 2026-12-31 |
| 5 | Markalı App | 2027-01-31 |

## 🔒 Güvenlik

- CSRF token validation
- JWT authentication (mobil app)
- KVKK compliance (veri silme)
- HTTPS ready
- Rate limiting (Django Axes)
- Secret key management (.gitignore)

## 📖 Dokümantasyon

- [Architecture](docs/architecture.md) - Sistem tasarımı
- [Backlog](docs/backlog.md) - Product backlog
- [Tasks](docs/task.md) - Sprint görevleri
- [API Docs](docs/api.md) - API referansı (yakında)

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
**Son Güncelleme:** 2026-09-09
