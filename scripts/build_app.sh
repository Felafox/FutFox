#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────
# build_app.sh — Construye FutFox.app (aplicación nativa de macOS)
#
# Uso:
#   bash scripts/build_app.sh
#
# Crea FutFox.app en el directorio actual.
# Podés arrastrarla a /Applications para usarla como cualquier app.
# ──────────────────────────────────────────────────────────────────────────

set -e

APP_NAME="FutFox"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$PROJECT_DIR/build"
APP_BUNDLE="$BUILD_DIR/$APP_NAME.app"

echo "⚽ Construyendo $APP_NAME.app..."
echo "   Proyecto: $PROJECT_DIR"

# Limpiar build anterior
rm -rf "$APP_BUNDLE"

# ── Estructura del .app bundle ──────────────────────────────────────────
mkdir -p "$APP_BUNDLE/Contents/MacOS"
mkdir -p "$APP_BUNDLE/Contents/Resources"

# ── Info.plist ───────────────────────────────────────────────────────────
cat > "$APP_BUNDLE/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>FutFox</string>
    <key>CFBundleDisplayName</key>
    <string>FutFox</string>
    <key>CFBundleIdentifier</key>
    <string>com.futfox.app</string>
    <key>CFBundleVersion</key>
    <string>2.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>2.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>FutFoxLauncher</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSMinimumSystemVersion</key>
    <string>13.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <false/>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.sports</string>
</dict>
</plist>
PLIST

echo "   ✓ Info.plist creado"

# ── Copiar el launcher ───────────────────────────────────────────────────
LAUNCHER_SRC="$PROJECT_DIR/scripts/futfox_launcher.sh"
LAUNCHER_DST="$APP_BUNDLE/Contents/MacOS/FutFoxLauncher"

# Crear un wrapper que ejecute el launcher con la ruta hardcodeada del proyecto
# Crear el wrapper con ruta hardcodeada
cat > "$LAUNCHER_DST" << ENDWRAPPER
#!/bin/bash
# FutFox.app Launcher
PROJECT_DIR="$PROJECT_DIR"
LAUNCHER="\$PROJECT_DIR/scripts/futfox_launcher.sh"

if [ -f "\$LAUNCHER" ]; then
    exec bash "\$LAUNCHER"
else
    osascript -e 'display dialog "FutFox no puede iniciar.\n\nNo se encontró el archivo:\n'"\$LAUNCHER"'\n\nReinstalá la aplicación." buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi
ENDWRAPPER

chmod +x "$LAUNCHER_DST"
echo "   ✓ FutFoxLauncher creado"

# ── Crear ícono (emoji ⚽ generado con sips) ─────────────────────────────
ICON_DIR="$APP_BUNDLE/Contents/Resources"
# Generar un PNG simple con el emoji ⚽ usando Python
python3 -c "
import subprocess, os
# Crear un PNG de 512x512 con fondo verde y el emoji ⚽
from PIL import Image, ImageDraw, ImageFont
img = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
# Círculo verde
draw.ellipse([56, 56, 456, 456], fill=(22, 163, 74))
draw.ellipse([56, 56, 456, 456], outline=(255, 255, 255, 80), width=8)
# Texto ⚽ centrado
try:
    font = ImageFont.truetype('/System/Library/Fonts/Apple Color Emoji.ttc', 220)
except:
    font = ImageFont.load_default()
draw.text((256, 256), '⚽', fill=(255, 255, 255), font=font, anchor='mm')
img.save('$ICON_DIR/AppIcon.png')
print('   ✓ AppIcon.png creado')
" 2>/dev/null || echo "   ⚠ No se pudo crear el ícono (PIL no instalado). Usando ícono genérico."

# Si tenemos el PNG, convertirlo a .icns
if [ -f "$ICON_DIR/AppIcon.png" ]; then
    # Crear directorio temporal para iconset
    ICONSET="$BUILD_DIR/futfox.iconset"
    rm -rf "$ICONSET"
    mkdir -p "$ICONSET"

    sips -z 16 16     "$ICON_DIR/AppIcon.png" --out "$ICONSET/icon_16x16.png" 2>/dev/null
    sips -z 32 32     "$ICON_DIR/AppIcon.png" --out "$ICONSET/icon_16x16@2x.png" 2>/dev/null
    sips -z 32 32     "$ICON_DIR/AppIcon.png" --out "$ICONSET/icon_32x32.png" 2>/dev/null
    sips -z 64 64     "$ICON_DIR/AppIcon.png" --out "$ICONSET/icon_32x32@2x.png" 2>/dev/null
    sips -z 128 128   "$ICON_DIR/AppIcon.png" --out "$ICONSET/icon_128x128.png" 2>/dev/null
    sips -z 256 256   "$ICON_DIR/AppIcon.png" --out "$ICONSET/icon_128x128@2x.png" 2>/dev/null
    sips -z 256 256   "$ICON_DIR/AppIcon.png" --out "$ICONSET/icon_256x256.png" 2>/dev/null
    sips -z 512 512   "$ICON_DIR/AppIcon.png" --out "$ICONSET/icon_256x256@2x.png" 2>/dev/null
    sips -z 512 512   "$ICON_DIR/AppIcon.png" --out "$ICONSET/icon_512x512.png" 2>/dev/null
    sips -z 1024 1024 "$ICON_DIR/AppIcon.png" --out "$ICONSET/icon_512x512@2x.png" 2>/dev/null

    iconutil -c icns "$ICONSET" -o "$ICON_DIR/AppIcon.icns" 2>/dev/null && \
        echo "   ✓ AppIcon.icns creado" || \
        echo "   ⚠ No se pudo generar .icns"
    rm -rf "$ICONSET"
fi

# ── Crear alias en Desktop ───────────────────────────────────────────────
DESKTOP_ALIAS="$HOME/Desktop/$APP_NAME.app"
rm -rf "$DESKTOP_ALIAS"
ln -s "$APP_BUNDLE" "$DESKTOP_ALIAS" 2>/dev/null && \
    echo "   ✓ Alias creado en el Escritorio" || true

echo ""
echo "══════════════════════════════════════════════════════════════"
echo "  ✅ $APP_NAME.app construida exitosamente"
echo ""
echo "  📍 Ubicación: $APP_BUNDLE"
echo "  🖥️  Escritorio: $DESKTOP_ALIAS"
echo ""
echo "  🚀 Podés arrastrar FutFox.app a /Applications"
echo "     o hacer doble clic para iniciar."
echo ""
echo "  💡 La app abre automáticamente tu navegador en:"
echo "     http://localhost:8501"
echo "══════════════════════════════════════════════════════════════"