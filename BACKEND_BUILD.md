# Photexx Studio - Backend Build Guide

Bu rehber, Flask backend'ini PyInstaller ile standalone executable'a çevirme adımlarını açıklar.

## Gereksinimler

```bash
pip install pyinstaller
pip install -r backend/requirements.txt
```

## Windows için Build

```powershell
cd backend
pyinstaller --clean server.spec
```

Çıktı: `backend/dist/photexx-backend.exe`

## Mac için Build

```bash
cd backend
pyinstaller --clean server.spec
```

Çıktı: `backend/dist/photexx-backend.app`

## Electron Build İçin Hazırlık

Backend executable oluşturulduktan sonra:

1. Backend dist klasörü mevcut olmalı: `backend/dist/`
2. Electron build çalıştır: `npm run build:mac` veya `npm run build:win`
3. Electron Builder otomatik olarak backend'i `extraResources` olarak paketleyecek

## Build Workflow (Tam Süreç)

### Mac'te:
```bash
# 1. Backend'i build et
cd backend
pyinstaller --clean server.spec
cd ..

# 2. Electron uygulamasını build et
npm run build:mac
```

### Windows'ta:
```powershell
# 1. Backend'i build et
cd backend
pyinstaller --clean server.spec
cd ..

# 2. Electron uygulamasını build et
npm run build:win
```

## Nasıl Çalışır?

1. **Backend Executable**: PyInstaller, Flask server + tüm dependencies'i tek bir dosyaya paketler
2. **Electron Startup**: `main.js` başlarken backend'i otomatik olarak başlatır
3. **Port Check**: Eğer port 5000 zaten kullanılıyorsa (backend zaten çalışıyorsa), yeni backend başlatmaz
4. **Cleanup**: Electron kapanırken backend process'i otomatik olarak sonlandırır

## Test Etme

Development mode'da test etmek için:

```bash
# Backend'i ayrı terminalde manuel başlat
cd backend
python server_standalone.py

# Electron'u başka terminalde başlat
npm start
```

## Önemli Notlar

- Backend executable ilk çalıştığında `~/.photexx/` klasörü oluşturur
- Upload ve preset dosyaları bu klasöre kaydedilir
- Her platform için ayrı build gereklidir (cross-platform build desteklenmez)

## Sorun Giderme

**Backend başlamıyor:**
- `backend/dist/` klasörünü kontrol edin
- PyInstaller build loglarını inceleyin
- Port 5000'in başka program tarafından kullanılmadığından emin olun

**Electron build hatası:**
- `backend/dist/` klasörünün mevcut olduğundan emin olun
- `npm install` komutunu tekrar çalıştırın
- `node_modules` ve `dist` klasörlerini silip yeniden build edin
