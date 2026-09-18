# ARCHITECTURE.md — GYM Platform Mimari Belgesi

**Son doğrulama:** 14 Eylül 2026 (uçtan uca test edilmiş, gerçek DB
şemasına göre yazılmıştır — bkz. `SPRINT1_VERIFICATION_REPORT.md`)

## Genel Bakış

GYM, [wger](https://github.com/wger-project/wger) açık kaynak fitness
platformu üzerine inşa edilmiş, Türkiye'deki spor salonları için
üyelik/paket/ödeme/ders yönetimi ekleyen bir genişletme katmanıdır.
wger'ın kendi kod tabanına dokunulmadan, ayrı bir `gym` Django app'i
olarak geliştirilmiştir.

**Platform:** Django 5.0 (wger üzerinden), PostgreSQL 15
**VPS:** Contabo (vmi3389964), gym.powerbi.com.tr
**Dil:** Python 3.12
**Container:** Docker Compose (nginx, web, db, cache, celery_worker, celery_beat)

---

## Mimari Katmanlar
┌─────────────────────────────────────────────────────────────┐
│ Client Layer │
│ (React Web App — planlanan, React Native Mobile — planlanan)│
└──────────────────────────┬──────────────────────────────────┘
│
┌──────────────────────────▼──────────────────────────────────┐
│ Nginx Reverse Proxy (port 8090) │
└──────────────────────────┬──────────────────────────────────┘
│
───────────┘
│
┌──────────────────────────▼──────────────────────────────────┐
│ Django REST API — Gunicorn (custom image) │
│ ROOT_URLCONF = 'wger.gym.custom_urls' (bkz. INFRASTRUCTURE.md)│
│ ┌─────────────────────────────────────────────────────┐ │
│ │ gym app (bind-mounted, kalıcı) │ │
│ │ ├─ models/new_models.py (5 model) │ │
│ │ ├─ serializers.py (5 ModelSerializer) │ │
│ │ ├─ views_api.py (6 ViewSet) │ │
│ │ ├─ urls_api.py (DefaultRouter) │ │
│ │ ├─ custom_urls.py (ROOT_URLCONF override) │ │
│ │ └─ admin.py │ │
│ │ │ │
│ │ wger (inherited, unmodified) │ │
│ └─────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────────┘
│
┌──────────────────┼──────────────────┬───────────────┐
│ │ │ │
┌───────▼────┐ ┌──────────▼──────┐ ┌───────▼────┐ ┌────────▼─────┐
│ PostgreSQL │ │ Redis │ │ Celery │ │ iyzipay SDK │
│ (Database) │ │ (Cache) │ │(worker/beat)│ │ (Sprint 2) │
└────────────┘ └─────────────────┘ └────────────┘ └──────────────┘

---

## Veri Modeli — Gerçek DB Şeması (14 Eylül 2026 doğrulandı)

> Aşağıdaki alanlar `information_schema.columns` sorgusuyla doğrudan
> DB'den çekilip modelle karşılaştırılmıştır. Sadece belgede yazan değil,
> **gerçekten var olan** şema budur.

### `gym_package`
| Alan | Tip | Not |
|---|---|---|
| id | integer PK | |
| gym_id | FK → gym.Gym | CASCADE |
| name | varchar | |
| package_type | varchar | monthly / yearly / freeze |
| price | numeric | >= 0 (validator) |
| duration_days | integer | |
| features | jsonb | serbest metadata |
| is_active | boolean | |
| created_at | timestamptz | auto_now_add |
| updated_at | timestamptz | auto_now |

### `gym_membership`
| Alan | Tip | Not |
|---|---|---|
| id | integer PK | |
| gym_id | FK → gym.Gym | CASCADE |
| user_id | FK → auth.User | CASCADE |
| package_id | FK → gym_package | **PROTECT** (aktif üyeliği olan paket silinemez) |
| start_date | date | |
| end_date | date | validasyon: start_date < end_date |
| status | varchar | active / expired / frozen / cancelled |
| frozen_until | date | nullable |
| created_at, updated_at | timestamptz | |

Property: `is_currently_active` — `status == active` ve bugün
`start_date`–`end_date` arasındaysa `True`.

### `gym_payment`
| Alan | Tip | Not |
|---|---|---|
| id | integer PK | |
| membership_id | FK → gym_membership | CASCADE |
| amount | numeric | >= 0 |
| payment_method | varchar | iyzico / cash |
| status | varchar | pending / completed / failed / refunded |
| transaction_id | varchar | nullable, unique |
| raw_response | jsonb | nullable — iyzico ham yanıtı için ayrılmış |
| note | text | nullable |
| created_at, updated_at | timestamptz | |

### `gym_gymclass`
| Alan | Tip | Not |
|---|---|---|
| id | integer PK | |
| gym_id | FK → gym.Gym | CASCADE |
| name | varchar | |
| trainer_id | FK → auth.User | SET_NULL, nullable |
| schedule | jsonb | `{day, start_time, end_time}` serbest format |
| capacity | integer | default 20 |
| description | text | nullable |
| is_active | boolean | |
| created_at, updated_at | timestamptz | |

Property: `available_slots` = `capacity - enrolled(cancelled=False).count()`

### `gym_classenrollment`
| Alan | Tip | Not |
|---|---|---|
| id | integer PK | |
| gym_class_id | FK → gym_gymclass | CASCADE |
| user_id | FK → auth.User | CASCADE |
| attended | boolean | |
| cancelled | boolean | soft-delete flag |
| enrolled_at | timestamptz | auto_now_add |
| updated_at | timestamptz | auto_now |

Constraint: `unique_together(gym_class, user)` — DB seviyesinde
uygulanıyor, ama serializer'da **elle** de kontrol ediliyor çünkü
DRF'in otomatik `UniqueTogetherValidator`'ı `user` alanını zorunlu
kılıp `ViewSet.perform_create()`'in enjeksiyon deseniyle çakışıyordu
(detay: `SPRINT1_VERIFICATION_REPORT.md`).

---

## API Katmanı

### ViewSet'ler ve İzin Modeli

| ViewSet | Okuma | Yazma | Özel notlar |
|---|---|---|---|
| PackageViewSet | Herkes (`IsAuthenticatedOrReadOnly`) | Auth gerekli | |
| MembershipViewSet | Sadece kendi kayıtları (staff → tümü) | Auth gerekli | `perform_create` ile `user` otomatik enjekte edilir |
| PaymentViewSet | Sadece kendi üyeliğine ait ödemeler (staff → tümü) | Auth gerekli | `membership__user=user` filtresi |
| GymClassViewSet | Herkes | Auth gerekli | Sadece `is_active=True` listelenir |
| ClassEnrollmentViewSet | Sadece kendi kayıtları (staff → tümü) | Auth gerekli | Kapasite + duplicate kontrolü serializer'da |
| DashboardViewSet | Sadece staff (`IsAdminUser`) | — (salt okunur `ViewSet`) | Aggregation, DB'ye her istekte gerçek zamanlı sorgu |

### Authentication — Gerçek Doğrulanmış Yöntem

wger'ın `REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']` ayarı:
```python
(
    'rest_framework.authentication.SessionAuthentication',
    'wger.utils.timezone_auth.TimezoneTokenAuthentication',  # ← kullandığımız
    'wger.utils.headless_auth.HeadlessJWTAuthentication',
    'wger.utils.oidc_auth.OidcTokenAuthentication',
    'wger.utils.timezone_auth.TimezoneJWTAuthentication',
)
```

**Kullanılan/doğrulanan yöntem:** `TimezoneTokenAuthentication` (DRF'in
klasik `TokenAuthentication`'ının bir uzantısı). Header formatı:
Authorization: Token <key>
Token, `rest_framework.authtoken.models.Token.objects.get_or_create(user=...)`
ile üretilir.

**Kullanılmayan/araştırılmamış:** JWT akışı bu kurulumda
`django-allauth`'ın "headless" OIDC modülü üzerinden yürüyor
(`path('allauth/', include('allauth.headless.urls'))`), **klasik
`simplejwt` `TokenObtainPairView` akışı değil**. `/api/v2/token/obtain/`
gibi bir endpoint bu kurulumda yoktur. Bu detay Sprint 1'in ilk
dokümantasyonunda yanlış yazılmıştı; API.md'de düzeltildi.

---

## Kalıcılık ve Deployment Stratejisi

**Kritik:** `docker.io/wger/server:latest` resmi image, `gym` app kodu
için **kaynak olarak değiştirilemez** — her değişikliğin kalıcı olması
için bind mount veya custom Dockerfile şart. Detaylı gerekçe ve
kurulum adımları için **`INFRASTRUCTURE.md`**'ye bakın. Özet:

- `gym/` app kodu → host'ta (`custom-code/gym/`), bind mount ile kalıcı
- `settings/main.py` (ROOT_URLCONF override içerir) → host'ta, bind mount ile kalıcı
- `iyzipay` SDK'sı → `Dockerfile.gym` ile image'a gömülü (build gerekir)
- `wger/urls.py` → **hiç değiştirilmez**, `custom_urls.py` üzerinden sarmalanır

---

## Sprint 2 — iyzico Entegrasyon Planı (mimari taslak)

> Bu bölüm henüz kod olarak yazılmadı, planlama amaçlıdır.
Client → POST /api/v2/gym/payments/checkout/
│
▼
PaymentService.create_checkout(membership, amount)
│
├─→ iyzipay.CheckoutFormInitialize.create(...)
│ (sandbox/prod anahtarları env'den)
│
▼
Payment kaydı oluşturulur (status='pending', raw_response=iyzico yanıtı)
│
▼
Client'a checkout_form_content / payment_page_url döner

--- Asenkron akış ---

iyzico → POST /api/v2/gym/payments/webhook/ (AllowAny — DRF auth değil,
iyzico imza doğrulaması)
│
▼
Signature doğrula (iyzico secret key ile HMAC)
│
▼
İlgili Payment kaydını bul (transaction_id / conversationId ile)
│
▼
status güncelle (completed/failed) + Membership.status senkronize et
│
▼
(Celery task) Email bildirimi gönder

**Önemli mimari kararlar (netleştirilmesi gerekenler):**
- Webhook endpoint'i kullanıcı auth'u gerektirmemeli (iyzico bizim
  token'ımızı bilmiyor) — `permission_classes = [AllowAny]` + iyzico'nun
  kendi imza mekanizmasıyla güvenlik sağlanmalı. **İmplement edildi ve
  doğrulandı** (18 Eylül 2026) — `PaymentService.handle_webhook()` +
  `PaymentViewSet.webhook` action'ı. Gerçek şema, resmi iyzico
  dokümantasyonundan (docs.iyzico.com/en/advanced/webhook) teyit edildi:
  **HMAC-SHA256** (HMAC-SHA1 değil — önceki taslakta belirsizdi),
  `X-IYZ-SIGNATURE-V3` header'ı, HPP (CheckoutForm) formatı için
  `key = SECRET_KEY + iyziEventType + iyziPaymentId + token +
  paymentConversationId + status`, sonuç HEX ile encode edilir.
  `X-Iyz-Signature` ve `X-Iyz-Signature-V2` artık desteklenmiyor.
  ⚠️ **Kritik ön koşul:** `X-IYZ-SIGNATURE-V3` gönderimi hesapta
  varsayılan olarak KAPALI — sandbox/prod hesabında aktif etmek için
  `entegrasyon@iyzico.com` ile iletişime geçilmesi gerekiyor. Sandbox
  hesabı açılınca bu adım unutulmamalı, aksi halde webhook hiç imza
  header'ı almaz ve `PaymentService._verify_webhook_signature` her
  zaman `False` döner (mock modda zaten kasıtlı olarak hep `False`
  döner — bkz. services.py).
- Webhook işleme muhtemelen Celery'ye taşınmalı (Backlog Story 2'de
  belirtildiği gibi) — bu durumda `celery_worker` servisinin de
  `Dockerfile.gym` ile build edilmesi gerekecek. **Bu adım tamamlandı**
  (bkz. SPRINT2_INFRASTRUCTURE_MIGRATION.md) — `celery_worker` ve
  `celery_beat` artık `Dockerfile.gym` ile build ediliyor, `iyzipay`
  import edilebiliyor.
- `Payment.raw_response` alanı zaten JSON tipinde ve bu amaç için
  ayrılmış — iyzico'nun tam yanıtı buraya yazılabilir. **İmplement
  edildi** — hem checkout hem webhook yanıtları parse edilmeden
  olduğu gibi bu alana yazılıyor.

---

## İlgili Dokümanlar

- `INFRASTRUCTURE.md` — kalıcılık stratejisi, bind mount'lar, custom Dockerfile
- `SPRINT1_VERIFICATION_REPORT.md` — 13-14 Eylül doğrulama süreci, bulunan/düzeltilen sorunlar
- `API.md` — endpoint referansı, gerçek auth yöntemi
- `BACKLOG.md` — Sprint 2+ planları
