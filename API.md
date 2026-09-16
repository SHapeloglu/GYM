# 📡 GYM API - Detaylı Referans

> REST API endpoints, request/response örnekleri ve kullanım rehberi

---

## 🚀 Quick Start

### Base URL
https://gym.powerbi.com.tr/api/v2/
Development: http://localhost:8090/api/v2/

### Authentication — ⚠️ 13 Eylül 2026'da düzeltildi

> **Önceki sürümdeki `/api/v2/token/obtain/` endpoint'i bu kurulumda
> mevcut değildi ve yanlış dokümante edilmişti.** Bu wger kurulumu,
> `django-allauth`'ın "headless" OIDC akışını kullanıyor ve
> `simplejwt`'in klasik `TokenObtainPairView`'i devrede değil. Aşağıda
> **gerçekten çalıştığı doğrulanmış** yöntem anlatılıyor.

**Gerçek çalışan yöntem: DRF Token Authentication**

`REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']` içinde tanımlı
`wger.utils.timezone_auth.TimezoneTokenAuthentication` (DRF'in klasik
`TokenAuthentication`'ının bir uzantısı) kullanılıyor. Token,
Django admin/shell üzerinden üretilebilir:

```python
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

user = User.objects.get(username='kullanici_adi')
token, created = Token.objects.get_or_create(user=user)
print(token.key)
```

İstekte kullanımı:
```bash
curl -H "Authorization: Token <token_key>" \
  https://gym.powerbi.com.tr/api/v2/gym/packages/
```

**Not:** Header formatı `Bearer` değil, **`Token`** anahtar kelimesiyle
başlıyor.

**JWT (opsiyonel, daha karmaşık):** JWT de teoride destekleniyor
(`wger.utils.headless_auth.HeadlessJWTAuthentication`,
`wger.utils.oidc_auth.OidcTokenAuthentication`), ancak bu, standart
`simplejwt` `/token/obtain/` akışı değil, `allauth`'ın headless OIDC
akışı (`/allauth/` altındaki endpoint'ler) üzerinden yürüyor. Sprint 2
kapsamında bu akışa girilmedi; mobil/web istemci JWT kullanmak isterse
bu bölüm ayrıca araştırılıp güncellenmeli.

**Hâlâ mevcut, çalışan yardımcı endpoint'ler:**
POST /api/v2/token/refresh # Mevcut bir JWT'yi yeniler (JWT akışı kullanılıyorsa)
POST /api/v2/token/verify # Bir JWT'nin geçerliliğini kontrol eder

---

## 📦 Package Endpoints

### 1. List All Packages

**Request:**
```http
GET /api/v2/gym/packages/
Authorization: Token <token_key>
```

**Query Parameters:**
?page=1
?page_size=50
?gym=1
?is_active=true
?ordering=price
?search=aylık

**Response:**
```json
{
  "count": 42,
  "next": "https://api.../packages/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "gym": 1,
      "name": "Aylık Paket",
      "package_type": "monthly",
      "price": "150.00",
      "duration_days": 30,
      "features": {
        "class_limit_per_week": 4,
        "trainer_sessions": 2
      },
      "is_active": true,
      "created_at": "2026-09-11T14:30:00Z",
      "updated_at": "2026-09-13T09:14:12Z"
    }
  ]
}
```

**Status Codes:**
- `200 OK` - Success
- `401 Unauthorized` - Missing/invalid token
- `403 Forbidden` - Permission denied

---

### 2. Create Package (Staff Only)

**Request:**
```http
POST /api/v2/gym/packages/
Authorization: Token <staff_token_key>
Content-Type: application/json

{
  "gym": 1,
  "name": "Premium Yıllık",
  "package_type": "yearly",
  "price": "1500.00",
  "duration_days": 365,
  "features": {
    "class_limit_per_week": "unlimited",
    "trainer_sessions": 10,
    "nutrition_plan": true
  },
  "is_active": true
}
```

**Response:** `201 Created` — 13 Eylül'de gerçek bir istekle doğrulandı ✅

**Validation Errors:** `400 Bad Request`
```json
{
  "price": ["Ensure this field is greater than or equal to 0."],
  "duration_days": ["This field may not be blank."]
}
```

---

## 👥 Membership Endpoints

### 1. List Memberships

**Request:**
```http
GET /api/v2/gym/memberships/
Authorization: Token <token_key>
```

**Response (gerçek doğrulanmış alanlar):**
```json
{
  "count": 5,
  "results": [
    {
      "id": 1,
      "gym": 1,
      "gym_name": "Main Gym",
      "user": 123,
      "user_username": "john",
      "package": 1,
      "package_detail": { "id": 1, "name": "Aylık Paket", "price": "150.00", "...": "..." },
      "start_date": "2026-09-11",
      "end_date": "2026-10-11",
      "status": "active",
      "frozen_until": null,
      "is_currently_active": true,
      "created_at": "2026-09-11T14:30:00Z",
      "updated_at": "2026-09-11T14:30:00Z"
    }
  ]
}
```

**User Isolation:** Regular user → sadece kendi üyeliklerini görür. Staff → tümünü görür.

### 2. Create Membership

**Request:**
```http
POST /api/v2/gym/memberships/
Authorization: Token <token_key>
Content-Type: application/json

{
  "package": 1,
  "start_date": "2026-09-11",
  "end_date": "2026-10-11",
  "status": "active"
}
```

**Not:** `user` ve `gym` alanları otomatik dolduruluyor — `user` istek
sahibinden, `gym` seçilen `package`'ın bağlı olduğu gym'den türetiliyor.
Staff kullanıcılar `user` alanını elle belirtebilir.

**Validasyon:** `end_date`, `start_date`'ten sonra olmalı, aksi halde:
```json
{"end_date": ["end_date must be after start_date."]}
```
13 Eylül'de gerçek istekle doğrulandı ✅

### 3. Get Active Memberships
```http
GET /api/v2/gym/memberships/active/
Authorization: Token <token_key>
```

---

## 💳 Payment Endpoints

### 1. List Payments
```http
GET /api/v2/gym/payments/
Authorization: Token <token_key>
```

**Response (gerçek doğrulanmış alanlar):**
```json
{
  "count": 12,
  "results": [
    {
      "id": 1,
      "membership": 1,
      "membership_detail": { "...": "..." },
      "amount": "150.00",
      "amount_display": "150.00₺",
      "payment_method": "cash",
      "status": "completed",
      "transaction_id": null,
      "raw_response": null,
      "note": null,
      "created_at": "2026-09-13T12:22:11Z",
      "updated_at": "2026-09-13T12:22:11Z"
    }
  ]
}
```

### 2. Create Payment
```http
POST /api/v2/gym/payments/
Authorization: Token <token_key>
Content-Type: application/json

{
  "membership": 1,
  "amount": "150.00",
  "payment_method": "cash",
  "status": "pending"
}
```
`payment_method` seçenekleri: `iyzico`, `cash`. `status` seçenekleri:
`pending`, `completed`, `failed`, `refunded`.

**Not:** Sprint 2'de bu endpoint iyzico checkout akışıyla genişletilecek
(ayrı bir `checkout/` action'ı planlanıyor, Backlog'a bakın).

---

## 🎓 Class Endpoints

### 1. List Classes
```http
GET /api/v2/gym/classes/
Authorization: Token <token_key>
```

**Response (gerçek doğrulanmış alanlar):**
```json
{
  "count": 12,
  "results": [
    {
      "id": 1,
      "gym": 1,
      "gym_name": "Main Gym",
      "name": "Yoga",
      "trainer": 5,
      "trainer_name": "John Doe",
      "schedule": { "day": "Monday", "start_time": "18:00", "end_time": "19:00" },
      "capacity": 20,
      "available_slots": 8,
      "enrolled_count": 12,
      "description": "Relaxing yoga session",
      "is_active": true,
      "created_at": "2026-09-11T14:30:00Z",
      "updated_at": "2026-09-11T14:30:00Z"
    }
  ]
}
```

### 2. Create Class (Staff Only)
```http
POST /api/v2/gym/classes/
Authorization: Token <staff_token_key>
Content-Type: application/json

{
  "gym": 1,
  "name": "HIIT Training",
  "trainer": 5,
  "schedule": { "day": "Tuesday", "start_time": "19:00", "end_time": "20:00" },
  "capacity": 15,
  "description": "High intensity interval training"
}
```

---

## 📝 Class Enrollment Endpoints

### 1. List Enrollments
```http
GET /api/v2/gym/class-enrollment/
Authorization: Token <token_key>
```

### 2. Enroll in Class
```http
POST /api/v2/gym/class-enrollment/
Authorization: Token <token_key>
Content-Type: application/json

{"gym_class": 1}
```
`user` otomatik olarak istek sahibinden dolduruluyor.

**Validation Errors:** `400 Bad Request`
```json
{"non_field_errors": ["Class capacity is full. Cannot enroll."]}
```
veya
```json
{"non_field_errors": ["User is already enrolled in this class."]}
```
İkisi de 13 Eylül'de gerçek isteklerle doğrulandı ✅

---

## 📊 Dashboard Endpoints

### 1. Get Dashboard Summary
```http
GET /api/v2/gym/dashboard/
Authorization: Token <staff_token_key>
```

**Response:**
```json
{
  "summary": {
    "active_members": 42,
    "monthly_revenue": "6300.00",
    "total_classes": 12,
    "total_revenue": "58500.00"
  },
  "generated_at": "2026-09-13T22:50:00Z"
}
```

**Permissions:** Staff/Admin only. 13 Eylül'de gerçek verilerle
agregasyonun doğru çalıştığı doğrulandı ✅

---

## ⚠️ Error Responses

### 400 Bad Request
```json
{"field_name": ["Error message"]}
```

### 401 Unauthorized
```json
{"detail": "Invalid token."}
```
(13 Eylül'de doğrulandı — geçersiz/silinmiş bir token bu mesajı döner)

### 403 Forbidden
```json
{"detail": "You do not have permission to perform this action."}
```

### 404 Not Found
```json
{"detail": "Not found."}
```

---

## 📚 Code Examples

### Python / Requests
```python
import requests
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

url = "https://gym.powerbi.com.tr/api/v2"

# Token, Django shell/admin üzerinden üretilir (bkz. Authentication bölümü)
token_key = "..."  # Token.objects.get_or_create(user=...) ile alınır

headers = {"Authorization": f"Token {token_key}"}

packages = requests.get(f"{url}/gym/packages/", headers=headers)
print(packages.json())

membership_data = {
    "package": 1,
    "start_date": "2026-09-11",
    "end_date": "2026-10-11",
    "status": "active"
}
membership = requests.post(
    f"{url}/gym/memberships/",
    json=membership_data,
    headers=headers
)
print(membership.json())
```

### cURL
```bash
curl -s -H "Authorization: Token <token_key>" \
  https://gym.powerbi.com.tr/api/v2/gym/packages/

curl -X POST https://gym.powerbi.com.tr/api/v2/gym/memberships/ \
  -H "Authorization: Token <token_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "package": 1,
    "start_date": "2026-09-11",
    "end_date": "2026-10-11",
    "status": "active"
  }'
```

---

## 📝 Changelog

### v1.0 (Sprint 1) — düzeltildi 13 Eylül 2026
- Package management ✅ (uçtan uca test edildi)
- Membership system ✅ (uçtan uca test edildi)
- Payment tracking ✅ (uçtan uca test edildi)
- Class scheduling ✅ (uçtan uca test edildi)
- Dashboard stats ✅ (uçtan uca test edildi)
- **Auth bölümü düzeltildi** — `/api/v2/token/obtain/` diye bir endpoint
  yoktu, gerçek yöntem (DRF Token Authentication) belgelendi

### v1.1 (Sprint 2 - Devam ediyor)
- iyzico SDK kuruldu (`iyzipay`, kalıcı Docker image içinde)
- Checkout endpoint'i (devam ediyor)
- Webhook handling (planlanan)
- Email bildirimleri (planlanan)

---

**API Version:** 1.0 (düzeltilmiş)
**Last Updated:** 14 Eylül 2026
**Status:** Uçtan uca test edildi, gerçekten çalışıyor ✅

Ayrıntılı doğrulama süreci için bkz. `SPRINT1_VERIFICATION_REPORT.md`
ve altyapı kalıcılık stratejisi için `INFRASTRUCTURE.md`.
