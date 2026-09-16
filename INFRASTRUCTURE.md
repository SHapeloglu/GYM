# 🏗️ Altyapı Notları — Kalıcılık Stratejisi

**Neden bu doküman var:** 13-14 Eylül 2026 oturumunda, önceki Sprint 1
çalışmasının `docker exec` ile container'ın yazılabilir katmanına doğrudan
dosya yazılarak yapıldığı, hiçbir kalıcılık mekanizması olmadan bırakıldığı
tespit edildi. Bu yüzden `serializers.py`, `urls_api.py`, bir migration
dosyası ve `wger/urls.py`'deki route kaydı **birden fazla kez** container
restart/recreate sonrasında kayboldu. Bu doküman, aynı hatayı bir daha
yapmamak için container'ın hangi kısımlarının kalıcı, hangilerinin geçici
olduğunu ve neden bu şekilde kurulduğunu açıklıyor.

**Kritik kural:** `docker.io/wger/server:latest` resmi image'ı **kaynak
kod olarak değiştirilmemeli**. Bind mount edilmeyen hiçbir dosya kalıcı
değildir — `docker exec` ile yazılan her şey bir sonraki `docker compose
down && up` veya `image pull`'da silinir.

---

## 1. Neden `Dockerfile` yoktu, sonra neden eklendi

Proje başta resmi `wger/server:latest` image'ını **hiç değiştirmeden**
kullanıyordu (`docker-compose.yml`'de sadece `image:` satırı vardı,
`build:` yoktu). Bu, hızlı başlangıç için makul bir seçimdi ama iki
sonucu oldu:

1. `pip install` gibi paket kurulumları kalıcı değildi.
2. Kaynak kod değişiklikleri (`gym/` app'i) de kalıcı değildi.

13-14 Eylül'de bu iki sorun da çözüldü — aşağıda nasıl olduğu anlatılıyor.

## 2. Bind Mount'lar (`docker-compose.yml` → `web` servisi)

```yaml
  web:
    build:
      context: .
      dockerfile: Dockerfile.gym
    volumes:
      - static:/home/wger/static
      - media:/home/wger/media
      - ../custom-code/gym:/home/wger/src/wger/gym
      - ../custom-code/main.py:/home/wger/src/settings/main.py
```

| Host'ta | Container'da | Ne için |
|---|---|---|
| `~/wger/custom-code/gym/` | `/home/wger/src/wger/gym/` | Tüm `gym` app kodu: models, serializers, views_api, urls_api, migrations, admin |
| `~/wger/custom-code/main.py` | `/home/wger/src/settings/main.py` | Deployment-özel Django ayarları + `ROOT_URLCONF` override |

**Neden `wger/urls.py`'yi doğrudan mount etmedik:** `urls.py` wger'ın
kendi framework dosyası. Onu bind mount edersek, wger image'ı
güncellendiğinde (yeni route'lar, yeni view'lar eklendiğinde) bizim
donmuş kopyamız o güncellemeleri **sessizce gölgeler** — üstelik hiçbir
hata vermeden, sadece yeni özellikler çalışmaz hale gelir. Bunun yerine
`ROOT_URLCONF` override yöntemi kullanıldı (aşağıya bakın).

## 3. `ROOT_URLCONF` Override — `wger/urls.py`'ye dokunmadan route ekleme

`wger/gym/custom_urls.py` (bind mount'lu `gym/` klasörünün içinde):

```python
from django.urls import include, path
from wger.urls import urlpatterns as _wger_urlpatterns

urlpatterns = _wger_urlpatterns + [
    path('api/v2/gym/', include('wger.gym.urls_api')),
]
```

`custom-code/main.py`'nin sonunda:
```python
ROOT_URLCONF = 'wger.gym.custom_urls'
```

Bu sayede Django, `wger.urls` yerine `wger.gym.custom_urls`'ı kök URL
yapılandırması olarak kullanıyor — ama bu dosya wger'ın orijinal
`urlpatterns`'ını olduğu gibi import edip üstüne sadece bizim `gym`
route'unu ekliyor. wger image'ı güncellenirse, `wger.urls` içindeki
her şey (import edildiği için) otomatik güncel kalır.

## 4. Custom Dockerfile — `iyzipay` SDK'sı için

`docker/Dockerfile.gym`:
```dockerfile
FROM docker.io/wger/server:latest
RUN pip install --no-cache-dir --break-system-packages iyzipay
```

**`--break-system-packages` neden gerekli:** Image'daki Python 3.12,
PEP 668 gereği sistem Python'ına doğrudan `pip install` yapılmasını
varsayılan olarak engelliyor. Bu bayrak olmadan build başarısız olur.

**Sadece `web` servisi bu Dockerfile'ı kullanıyor** (`build:` bloğu).
`nginx`, `celery_worker`, `celery_beat` servisleri hâlâ resmi
`image: docker.io/wger/server:latest`'i kullanıyor. Eğer Sprint 2'de
webhook işleme Celery'ye taşınırsa (Backlog Story 2'de planlandığı
gibi) ve Celery worker'ın da `iyzipay` importuna ihtiyacı olursa,
`celery_worker` servisinin de aynı `build:` bloğuna geçirilmesi
gerekecek.

## 5. Yeni bir paket/bağımlılık eklerken izlenecek yol

1. **Asla** `docker compose exec web pip install ...` ile tek başına
   kurmayın — geçici, bir sonraki recreate'te kaybolur.
2. `Dockerfile.gym`'e `RUN pip install --no-cache-dir --break-system-packages <paket>`
   satırı ekleyin (birden fazla paket varsa tek `RUN` satırında
   virgülle/boşlukla ayırıp birleştirin, katman sayısını azaltmak için).
3. `docker compose build web` çalıştırın.
4. `docker compose up -d web` ile yeni image'ı devreye alın.

## 6. Yeni bir `gym` app dosyası eklerken/düzenlerken izlenecek yol

`gym/` klasörünün tamamı zaten host'ta (`~/wger/custom-code/gym/`) ve
bind mount'lu olduğu için, **container içinde `docker exec` ile
düzenleme yapılan her değişiklik zaten host'a yazılıyor** — ekstra bir
adım gerekmiyor. Ama emin olmak için değişiklikten sonra:

```bash
docker compose exec web md5sum /home/wger/src/wger/gym/<dosya>
md5sum ~/wger/custom-code/gym/<dosya>
```

ile iki tarafın senkron olduğunu doğrulayın.

## 7. Yedekler

Tam `gym/` klasörünün bir tar yedeği burada duruyor:
~/gym-code-backup/gym-app-<tarih>.tar.gz
Herhangi bir felaket durumunda (yanlışlıkla silme, bozuk düzenleme) bu
yedekten geri dönülebilir.

## 8. Bilinen Sınırlama

`docker-compose.yml`'in kendisi **hâlâ kalıcı bir mekanizmayla
korunmuyor** — yani `docker-compose.yml`'in kendisi kaybolursa (host
diskinden silinirse), bind mount'lar ve `build:` yapılandırması da
gider. Ancak bu dosya zaten git ile versiyonlanan bir proje dosyası
olmalı; eğer henüz git'e commit edilmediyse, **ilk yapılması gereken
şey bunu commit etmektir.**
