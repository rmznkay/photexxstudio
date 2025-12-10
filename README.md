# 📸 Photexx Studio

Professional Photo Editing & Album Management Studio with Lightroom-style presets.

## ✨ Features

- 🎨 **Lightroom XMP Presets** - Import and apply Adobe Lightroom presets
- 🖼️ **RAW Support** - Full RAW image processing (NEF, CR2, ARW, etc.)
- 📁 **Album Management** - Organize photos in projects
- ⚡ **Real-time Preview** - Instant adjustment feedback
- 🔧 **Advanced Color Adjustments**:
  - Exposure, Contrast, Highlights, Shadows
  - Whites, Blacks, Vibrance, Saturation
  - Temperature, Tint, Sharpness
- 🖥️ **Cross-Platform** - Windows, macOS & Linux

## 🚀 Installation

### Mac
1. Download `Photexx-Studio.dmg` from [Releases](https://github.com/rmznkay/photexxstudio/releases)
2. Open the DMG file
3. Drag Photexx Studio to Applications

### Windows
1. Download `Photexx-Studio-Setup.exe` from [Releases](https://github.com/rmznkay/photexxstudio/releases)
2. Run the installer
3. Follow the installation wizard

### Linux
1. Download `Photexx-Studio.AppImage` from [Releases](https://github.com/rmznkay/photexxstudio/releases)
2. Make it executable: `chmod +x Photexx-Studio.AppImage`
3. Run the AppImage

## 🛠️ Development

```bash
# Clone repository
git clone https://github.com/rmznkay/photexxstudio.git
cd photexxstudio

# Install Node dependencies
npm install

# Install Python dependencies
cd backend
pip install -r requirements.txt
cd ..

# Start backend server
cd backend
python server.py

# Start app (in new terminal)
npm run dev
```

## 📦 Build

```bash
# Build for all platforms
npm run build:all

# Build for Mac (macOS only)
npm run build:mac

# Build for Windows
npm run build:win

# Build for Linux
npm run build:linux
```

## 📝 Requirements

- **Python 3.8+** - Backend image processing
- **Node.js 18+** - Electron app
- **Python packages**: Flask, Pillow, opencv-python, numpy, rawpy

## 🎯 Usage

1. Launch Photexx Studio
2. Create a new project or open existing
3. Import photos (JPG, PNG, RAW formats)
4. Apply Lightroom XMP presets or adjust manually
5. Export edited photos

## 📚 Adding Presets

1. Place `.xmp` files in the `presets/` folder
2. Presets automatically appear in the editor
3. Click a preset to apply all adjustments

## 🏗️ Technologies

- **Electron 28** - Desktop framework
- **Python + Flask** - Image processing backend
- **Pillow + OpenCV** - Image manipulation
- **rawpy** - RAW file support
- **Firebase** - Authentication
- **GitHub Actions** - Automated builds

## 📄 License

MIT

## 👨‍💻 Author

Photexx Studio Team
