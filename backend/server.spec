# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Photexx Backend Server
This packages the Flask server into a standalone executable
"""

block_cipher = None

a = Analysis(
    ['server_standalone.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'flask',
        'flask_cors',
        'PIL',
        'PIL.Image',
        'PIL.ImageEnhance',
        'PIL.ImageFilter',
        'PIL.ImageOps',
        'cv2',
        'numpy',
        'rawpy',
        'imageio',
        'werkzeug',
        'werkzeug.utils',
        'xml.etree.ElementTree',
        're',
        'json',
        'base64',
        'io',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='photexx-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# macOS app bundle
app = BUNDLE(
    exe,
    name='photexx-backend.app',
    icon=None,
    bundle_identifier='com.photexx.backend',
    version='1.0.0',
    info_plist={
        'NSHighResolutionCapable': 'True',
    },
)
