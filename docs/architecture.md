# GYM - Sistem Mimarisi

## Tech Stack
- **Backend:** Django 4.2 (Python 3.12)
- **Database:** PostgreSQL 15
- **Cache:** Redis
- **Task Queue:** Celery + Beat
- **API:** Django REST Framework
- **Frontend:** wger (Vue.js)
- **Containerization:** Docker + Docker Compose
- **Web Server:** Nginx
- **Payment:** iyzico (Türkiye)

## Mimarı
┌─────────────────────────────────────────┐
│ Nginx (Port 8090) │
├─────────────────────────────────────────┤
│ Django Web (Gunicorn) │
├──────┬──────────────────────────────┬──┤
│ │ │ │
│ PostgreSQL Redis Celery │
│ (Üyelik, (Cache) (Tasks) │
│ Ödeme, │
│ Ders) │
└──────┴──────────────────────────────┴──┘

## Modüller (MVP Fazı)

### 1. Membership Module
- Üyelik paketleri (aylık, yıllık, dondurma)
- Paket satışı ve yenileme
- Üyelik tarihi ve veri

### 2. Payment Module
- iyzico entegrasyonu
- Tekrarlayan ödeme (subscription)
- Ödeme geçmişi ve faturalama

### 3. Class Module
- Sınıf/ders programlama
- Kontenjan yönetimi
- Katılım takibi (wger'in egzersiz modülüne bağlı)

### 4. Dashboard Module
- Salon sahibi paneli
- Gelir raporları
- Üye istatistikleri

## Veritabanı Şeması (MVP)

```sql
-- Üyelik Paketleri
CREATE TABLE gym_packages (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    price DECIMAL(10,2),
    duration_days INT,
    features JSONB
);

-- Üyelikler
CREATE TABLE gym_memberships (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES auth_user,
    package_id INT REFERENCES gym_packages,
    start_date DATE,
    end_date DATE,
    status VARCHAR(20), -- active, expired, frozen
    created_at TIMESTAMP
);

-- Ödemeler
CREATE TABLE gym_payments (
    id SERIAL PRIMARY KEY,
    membership_id INT REFERENCES gym_memberships,
    amount DECIMAL(10,2),
    payment_method VARCHAR(20), -- iyzico, cash
    status VARCHAR(20), -- pending, completed, failed
    transaction_id VARCHAR(100),
    created_at TIMESTAMP
);

-- Sınıflar
CREATE TABLE gym_classes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    trainer_id INT REFERENCES auth_user,
    schedule JSONB, -- Gün/saat bilgisi
    capacity INT,
    created_at TIMESTAMP
);

-- Sınıf Katılımı
CREATE TABLE gym_class_enrollment (
    id SERIAL PRIMARY KEY,
    class_id INT REFERENCES gym_classes,
    user_id INT REFERENCES auth_user,
    attended BOOLEAN,
    enrolled_at TIMESTAMP
);
```

## API Endpoints (MVP)
POST /api/v2/gym/packages/ - Paket listesi
POST /api/v2/gym/memberships/ - Üyelik oluştur
GET /api/v2/gym/memberships/{id}/ - Üyelik detayı
PUT /api/v2/gym/memberships/{id}/ - Üyeliği güncelle
POST /api/v2/gym/payments/ - Ödeme yap
POST /api/v2/gym/classes/ - Sınıf listesi
POST /api/v2/gym/class-enrollment/ - Sınıfa kaydol
GET /api/v2/gym/dashboard/ - Dashboard verisi

## Deployment

- **Server:** Contabo (Ubuntu 24)
- **Docker:** Docker Compose (wger_network)
- **Domain:** gym.powerbi.com.tr:8090
- **Database:** PostgreSQL 15 (docker-db-1)
- **Cache:** Redis (docker-cache-1)

## Security
- CSRF token validation
- JWT for mobile app
- HTTPS ready (behind reverse proxy)
- Rate limiting (Django Axes)
- KVKK compliance (veri silme)
