# Darktable Kurulum Rehberi

Photexx Studio, professional grade RAW işleme için darktable kullanabilir.

## Mac Kurulum

```bash
# Homebrew ile (Önerilen)
brew install --cask darktable

# Veya direct download
# https://www.darktable.org/install/#macos
```

## Windows Kurulum

```powershell
# winget ile (Önerilen)
winget install darktable.darktable

# Veya direct download
# https://www.darktable.org/install/#windows
```

## Kurulum Kontrolü

Terminal'de:
```bash
darktable-cli --version
```

Eğer version numarası görünüyorsa kurulum başarılı.

## Backend Yeniden Başlatma

Darktable kurduktan sonra backend'i yeniden başlatın:

```bash
cd backend
python3 server_standalone.py
```

Backend başlarken şunu göreceksiniz:
```
🚀 Photexx Backend Server Starting...
✅ Darktable-cli found: version X.X.X
```

## Nasıl Çalışır?

- RAW dosya + XMP preset → darktable otomatik işler
- JPG dosya → Custom processor kullanılır
- Darktable yoksa → Otomatik fallback custom processor'a

## Avantajlar

- ✅ %100 Lightroom uyumlu XMP processing
- ✅ Professional color science
- ✅ Tüm Lightroom ayarları (HSL, Curves, Split Toning, etc.)
- ✅ Hızlı ve optimize edilmiş

## Sorun Giderme

**"darktable-cli not found"**
- Darktable kurulu olduğundan emin olun
- Terminal'i yeniden açın
- PATH'e eklendiğinden emin olun

**Mac'te PATH sorunu:**
```bash
export PATH="/Applications/darktable.app/Contents/MacOS:$PATH"
```

**Windows'ta PATH sorunu:**
```powershell
$env:Path += ";C:\Program Files\darktable\bin"
```
