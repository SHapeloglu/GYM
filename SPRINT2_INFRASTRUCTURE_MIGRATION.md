# 🚚 Sprint 2 — Altyapı Taşıma ve Cutover Raporu

**Tarih:** 16-18 Eylül 2026
**Amaç:** `celery_worker`/`celery_beat` servislerini `Dockerfile.gym` ile
build etmek (iyzico Sprint 2 hazırlığı, bkz. INFRASTRUCTURE.md §4) ve bu
sırada ortaya çıkan `docker/` submodule kirliliğini gidermek.

**Sonuç:** Deployment config artık ana repoda, `wger-project/docker`
upstream'i temiz, sırlar yenilendi, prod verisi kayıpsız yeni stack'e
taşındı. Süreçte üç ayrı risk anı yaşandı ve hepsi çözüldü — bu doküman
onların kaydı, aynı hataların tekrarlanmaması için.

---

## ⚠️ Bulunan Sorunlar (başlangıç durumu)

1. **`docker/` submodule'ü kirliydi.** `~/wger/docker`, remote'u
   `wger-project/docker` (halka açık upstream) olan bir repoydu ve
   içinde **push edilmemiş 1 commit** vardı: `docker-compose.yml`,
   `config/nginx.conf`, `config/prod.env` değişiklikleri. Bu commit hiç
   push edilmedi ama halka açık bir upstream'e bağlı repoda durması
   başlı başına risk.
2. **`prod.env`'de zayıf/tahmin edilebilir prod sırları vardı:**
   `SECRET_KEY=dj-insecure-...` (Django'nun development-only varsayılan
   anahtarı) ve `POSTGRES_PASSWORD=wger_db_secure_2024` (tahmin
   edilebilir kalıp).
3. **`docker-compose.yml` ve `Dockerfile.gym` hiçbir git reposunda
   commit'li değildi** — sadece VPS diskinde duruyorlardı. Disk kaybı
   durumunda kalıcılık altyapısının kendisi kaybolabilirdi
   (INFRASTRUCTURE.md §8'in tam olarak uyardığı durum).

## ✅ Uygulanan Çözüm

### 1. Deployment config'i ana repoya taşıma

`docker-compose.yml`, `Dockerfile.gym`, `config/nginx.conf`,
`services/postgres.yaml`, `services/redis.yaml` dosyaları
`~/wger/docker/` (submodule) içinden `~/wger/deploy/` (ana repo,
`SHapeloglu/GYM`) içine kopyalandı. `services/powersync.yaml` ve
`config-powersync/` **taşınmadı** — PowerSync bu kurulumda
kullanılmıyor.

`docker/` submodule'ü sonra `git reset --hard origin/master` ile
upstream'in temiz haline döndürüldü. `custom-code/gym/` bind mount'lu
olduğu için gerçek uygulama kodu bu işlemden etkilenmedi.

### 2. Sır rotasyonu

- `SECRET_KEY`: Django'nun `get_random_secret_key()` fonksiyonuyla
  yeniden üretildi.
- `POSTGRES_PASSWORD`: `openssl rand -base64 32` ile yeniden üretildi,
  `PS_DATABASE_URI` içindeki şifre de eşitlendi.
- `prod.env` **git'e commit edilmedi** — `.gitignore`'a eklendi.
  Yerine placeholder değerlerle (`CHANGE_ME`) bir
  `prod.env.example` commit edildi.

### 3. `celery_worker` / `celery_beat` build'e geçirildi

`deploy/docker-compose.yml`'de her iki servisin `image:
docker.io/wger/server:latest` satırı `web` servisiyle aynı `build:
{context: ., dockerfile: Dockerfile.gym}` bloğuyla değiştirildi.
Doğrulama:
```bash
docker compose exec celery_worker python3 -c "import iyzipay; print('iyzipay OK')"
```
→ `iyzipay OK`

### 4. Network izolasyonu — kritik bulgu

İlk `docker compose up -d` denemesinde `deploy` stack'i **eski
`docker` stack'iyle aynı `wger_network` adını** kullanıyordu
(`docker-compose.yml`'in sonunda `networks: default: name:
wger_network` sabit yazılıydı). Bu, iki ayrı Celery worker'ın
birbirini "komşu" olarak görmesine yol açtı (`missed heartbeat from
celery@<eski_container_id>` logu). Prod verisine yazma riski yoktu
(Celery pidbox/mingle seviyesinde bir karışıklıktı) ama kabul edilemez
bir durumdu.

**Çözüm:** `deploy/docker-compose.yml`'deki network adı
`gym_deploy_network` olarak değiştirildi — artık her stack kendi ayrı
network'ünde.

> **Kural:** Bir wger tabanlı stack'in birden fazla kopyası aynı
> host'ta çalışacaksa (test/prod, staging/prod, vb.), `docker-compose.yml`
> içindeki `networks.default.name` **her kopya için benzersiz olmalı**.
> Aksi halde Redis/Celery seviyesinde sessiz bir karışma olur.

### 5. Veri taşıma (pg_dump / pg_restore)

Yeni `deploy` stack'i ayağa kaldırıldığında **kendi boş
`deploy_postgres-data` volume'unu** kullandığı fark edildi — eski
`docker_postgres-data` volume'undaki gerçek veriye bağlı değildi.
İşlem sırası:

1. Eski `docker-db-1`'den tam yedek alındı:
   ```bash
   docker exec docker-db-1 pg_dump -U wger -d wger -F c -f /tmp/wger_backup.dump
   docker cp docker-db-1:/tmp/wger_backup.dump ~/wger-code-backup/wger_backup_20260917_121834.dump
   ```
   (274 MB, custom format)
2. Eski stack'in tüm container'ları durduruldu (`docker stop ...`) —
   `docker compose down` `services.db conflicts with imported
   resource` hatasıyla başarısız olduğu için doğrudan `docker stop`
   kullanıldı.
3. Yeni stack'in boş `deploy_postgres-data` volume'u silindi, `db`
   servisi tekrar başlatıldı (temiz, boş DB ile).
4. Yedek, yeni `deploy-db-1`'e restore edildi:
   ```bash
   docker exec deploy-db-1 pg_restore -U wger -d wger --clean --if-exists -v /tmp/restore.dump
   ```
5. Doğrulama: `gym_package`/`gym_membership` sayıları `0` döndü — bu
   **beklenen sonuç**, çünkü SPRINT1_VERIFICATION_REPORT.md'de test
   verisinin temizlendiği zaten belgelenmişti.

**Yedek dosyası hâlâ duruyor:**
`~/wger-code-backup/wger_backup_20260917_121834.dump` — birkaç gün
saklanıp sonra silinebilir.

### 6. Cutover

- Eski `docker-nginx-1` durdurulup port `8090` boşaltıldı.
- `deploy-nginx-1`, network değişimi nedeniyle stale DNS önbelleğiyle
  `host not found in upstream "web:8000"` hatası verdi (21 saat önce,
  eski network aktifken oluşturulmuş bir container'dı). Çözüm:
  ```bash
  docker compose rm -sf nginx
  docker compose up -d nginx
  ```
  Container'ı sıfırdan yeniden oluşturmak DNS'i güncel network'e göre
  tazeledi.
- Eski `docker-*` container'ları tamamen silindi (`docker rm`).
  `docker_postgres-data` volume'u yedek amaçlı **silinmedi**, birkaç
  gün sonra silinebilir.

**Son doğrulama:**
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8090/api/v2/version/
# → 200
curl -s -H "Authorization: Token <token>" http://localhost:8090/api/v2/gym/packages/
# → {"count":0,"next":null,"previous":null,"results":[]}
```

---

## 📌 Çıkarılan Dersler

1. **`docker compose down` her zaman temiz çalışmayabilir.** `include:`
   ile başka compose dosyalarını dahil eden projelerde (`services/postgres.yaml`
   gibi) `services.db conflicts with imported resource` hatası
   alınabilir. Bu durumda `docker stop <container...>` ile doğrudan
   container'ları durdurmak güvenli bir alternatiftir (volume'lara
   dokunmaz).
2. **Named volume'lar proje adına göre öneklenir.** Bir compose
   projesini yeniden konumlandırırken (`docker/` → `deploy/`), proje
   adı değiştiği için (`docker_postgres-data` → `deploy_postgres-data`)
   volume'lar da değişir — eski veri otomatik olarak görünmez.
   **Taşıma öncesi mutlaka `docker volume ls` ile kontrol edilmeli.**
3. **Network adı sabitse (`name:` alanı), iki kopya çakışır.** Bu,
   sadece port çakışmasından farklı ve daha sinsi bir sorun — servisler
   ayağa kalkar ama birbirine karışır.
4. **Container'lar DNS/network konfigürasyonunu yeniden okumaz.**
   Network adı değiştiğinde, o network değişiminden önce oluşturulmuş
   container'lar `docker compose up -d` ile "restart" edilse bile eski
   DNS durumunda kalabilir. `rm -sf` + `up -d` ile sıfırdan yeniden
   oluşturmak gerekir.

## İlgili Dokümanlar

- `INFRASTRUCTURE.md` — genel kalıcılık stratejisi (bu doküman onun
  Sprint 2 başında yaşanan somut bir uygulamasının kaydıdır)
- `SPRINT1_VERIFICATION_REPORT.md` — Sprint 1 doğrulama süreci
