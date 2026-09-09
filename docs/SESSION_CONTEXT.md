# Session Context & Setup

## ✅ Tamamlanan (2026-09-09)

### Kurulum
- [x] wger Docker kurulumu (gym.powerbi.com.tr:8090)
- [x] PostgreSQL 15 (docker-db-1)
- [x] Redis cache (docker-cache-1)
- [x] Nginx reverse proxy
- [x] Admin kullanıcı oluşturma (username: info)

### Konfigürasyon
- [x] SECRET_KEY ve SITE_URL ayarlandı
- [x] CSRF_TRUSTED_ORIGINS eklendi
- [x] iyzico API keys hazır (test mode)
- [x] Türkçe dil desteği (ayarlanacak)

### Git & Dokümantasyon
- [x] GitHub repo: https://github.com/SHapeloglu/GYM
- [x] architecture.md, backlog.md, task.md, progress.md oluşturuldu
- [x] README.md yazıldı
- [x] .gitignore oluşturuldu (prod.env gizli)

---

## 🎯 Sonraki Sprint (Faz 1: Üyelik + Ödeme + Ders)

### Başlangıç Checklist

```bash
# 1. Sunucuya bağlan
ssh root@95.111.242.96

# 2. wger docker'ı başlat (durduysa)
cd ~/wger/docker
docker compose up -d
docker compose ps  # Tüm container'lar healthy olmalı

# 3. Django app oluştur
docker compose exec web python3 manage.py startapp gym

# 4. Models yazacağız (Sonraki adım)
```

---

## 📋 Server & Erişim Bilgileri

| Bilgi | Değer |
|-------|-------|
| **Server IP** | 95.111.242.96 |
| **Domain** | gym.powerbi.com.tr:8090 |
| **SSH User** | root |
| **Docker Network** | wger_network |
| **Web Container** | docker-web-1 |
| **DB Container** | docker-db-1 |
| **Admin User** | info (şifre: ?) |
| **GitHub** | https://github.com/SHapeloglu/GYM |

---

## 🔑 Önemli Dosyalar & Lokasyonlar

| Dosya | Lokasyon | Not |
|-------|----------|-----|
| docker-compose.yml | ~/wger/docker/ | Container konfigürasyonu |
| prod.env | ~/wger/docker/config/ | SECRET (git'te yok) |
| nginx.conf | ~/wger/docker/config/ | Web server config |
| Django Apps | ~/wger/wger/src/ | wger fork |
| Dokümantasyon | ~/wger/docs/ | Git'te var |

---

## 💾 Database Info
Database: wger
User: wger
Password: wger_db_secure_2024
Host: docker-db-1:5432
Port: 5432

---

## 🚀 Devam Etmek İçin

### Yeni Session Başlatma
```bash
# 1. SSH'ye bağlan
ssh root@95.111.242.96

# 2. Docker'ı kontrol et
cd ~/wger/docker
docker compose ps

# 3. Logs kontrol et (problem varsa)
docker compose logs web -n 20

# 4. Django shell (test için)
docker compose exec web python3 manage.py shell
```

### Git Pull (Güncellemeler için)
```bash
cd ~/wger
git pull origin main
```

### Yeni Commit Yapmak
```bash
cd ~/wger
git add .
git commit -m "Açıklama"
git push origin main
```

---

## 📝 MVP Faz 1 Adımları

1. **Django Gym App** oluştur
2. **Models** yaz (Package, Membership, Payment, Class)
3. **Migrations** yap
4. **Serializers** (DRF)
5. **ViewSets** (API endpoints)
6. **Admin Panel** konfigürasyonu
7. **iyzico SDK** entegrasyonu
8. **Testing**

---

## ⚠️ Dikkat Edilecekler

- **prod.env:** GitHub'a PUSH ETME (gizli)
- **Backups:** PostgreSQL veritabanını düzenli backup al
- **Logs:** Hata varsa `docker compose logs` ile kontrol et
- **Updates:** wger fork'unu ana repo'dan senkronize et

---

## 📞 Problemi Çözmek İçin

### Container crash ediyor
```bash
docker compose restart web
docker compose logs web -n 50
```

### Database bağlantısı yok
```bash
docker compose exec db psql -U wger -d wger -c "SELECT 1"
```

### Static files problem
```bash
docker compose exec web python3 manage.py collectstatic --no-input --clear
docker compose restart nginx
```

---

**Güncellenme Tarihi:** 2026-09-09 23:59
**Sonraki Session:** [Tarih]
