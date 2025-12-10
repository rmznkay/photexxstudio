# Photexx Studio

Professional Photo Editing & Album Management Suite

## Özellikler

✨ **Modern UI** - Buzlu iOS/Apple tarzı glassmorphic arayüz
🔐 **Firebase Auth** - Güvenli firma kullanıcı girişi
🖥️ **Cross-Platform** - Windows & macOS desteği
⚡ **Electron** - Hızlı ve native desktop deneyimi

## Kurulum

```bash
# Bağımlılıkları yükle
npm install

# Uygulamayı başlat
npm start

# Development mode
npm run dev
```

## Yapı

```
Photexx Studio/
├── main.js              # Electron ana dosya
├── index.html           # Ana UI
├── styles.css           # Buzlu Apple UI stilleri
├── app.js               # Frontend logic
├── firebase-config.js   # Firebase yapılandırma
└── package.json         # Bağımlılıklar
```

## Firebase Yapılandırması

- Sadece `firma` field'ı olan kullanıcılar giriş yapabilir
- `users` koleksiyonunda firma kontrolü yapılır

## Teknolojiler

- Electron 28
- Firebase 10.7
- Modern ES6+ JavaScript
- Glassmorphic UI Design
