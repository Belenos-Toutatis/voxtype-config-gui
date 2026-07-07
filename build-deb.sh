#!/usr/bin/env bash
# Construit un paquet .deb installable pour l'éditeur de configuration VoxType.
# Aucune dépendance de build exotique : seulement dpkg-deb (+ fakeroot si dispo).
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SRC_DIR"

PKG="voxtype-config"
VERSION="0.2.1"
REVISION="1"
ARCH="all"                       # paquet Python pur, indépendant de l'architecture
MAINTAINER="Emmanuel Wenner <emmanuel.wenner@gmail.com>"
APP_ID="earth.tyler.VoxTypeConfig"

BUILD="$SRC_DIR/build"
ROOT="$BUILD/${PKG}_${VERSION}-${REVISION}_${ARCH}"

say() { printf '\033[1;34m==>\033[0m %s\n' "$1"; }

rm -rf "$ROOT"
mkdir -p "$ROOT/DEBIAN" \
         "$ROOT/usr/share/$PKG" \
         "$ROOT/usr/bin" \
         "$ROOT/usr/share/applications" \
         "$ROOT/usr/share/metainfo" \
         "$ROOT/usr/share/icons/hicolor/scalable/apps" \
         "$ROOT/usr/share/doc/$PKG"

# --- 1. Paquet Python -------------------------------------------------------
say "Copie du paquet Python"
cp -r "$SRC_DIR/voxtype_config" "$ROOT/usr/share/$PKG/"
# pas de bytecode pré-compilé dans le .deb
find "$ROOT/usr/share/$PKG" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

# --- 2. Lanceur -------------------------------------------------------------
say "Lanceur /usr/bin/$PKG"
cat > "$ROOT/usr/bin/$PKG" <<'PY'
#!/usr/bin/env python3
import sys
sys.path.insert(0, "/usr/share/voxtype-config")
from voxtype_config.app import main
sys.exit(main(sys.argv))
PY
chmod 755 "$ROOT/usr/bin/$PKG"

# --- 3. Entrée de menu + icône ---------------------------------------------
say "Fichier .desktop + icône + métadonnées AppStream"
install -m 644 "$SRC_DIR/data/$APP_ID.desktop" \
        "$ROOT/usr/share/applications/$APP_ID.desktop"
install -m 644 "$SRC_DIR/data/$APP_ID.svg" \
        "$ROOT/usr/share/icons/hicolor/scalable/apps/$APP_ID.svg"
install -m 644 "$SRC_DIR/data/$APP_ID.metainfo.xml" \
        "$ROOT/usr/share/metainfo/$APP_ID.metainfo.xml"

# --- 4. Documentation / copyright ------------------------------------------
install -m 644 "$SRC_DIR/README.md" "$ROOT/usr/share/doc/$PKG/README.md"
cat > "$ROOT/usr/share/doc/$PKG/copyright" <<EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: $PKG

Files: *
Copyright: $(date +%Y) Emmanuel Wenner
License: MIT
EOF

# --- 5. Métadonnées du paquet ----------------------------------------------
say "Génération de DEBIAN/control"
INSTALLED_KB=$(du -ks "$ROOT/usr" | cut -f1)
cat > "$ROOT/DEBIAN/control" <<EOF
Package: $PKG
Version: ${VERSION}-${REVISION}
Section: utils
Priority: optional
Architecture: $ARCH
Maintainer: $MAINTAINER
Installed-Size: $INSTALLED_KB
Depends: python3 (>= 3.10), python3-gi, gir1.2-gtk-4.0 (>= 4.0), gir1.2-adw-1 (>= 1.0), python3-tomlkit, python3-evdev
Recommends: voxtype
Description: Graphical configuration editor for VoxType
 A GTK4 / libadwaita interface to fully configure VoxType (voice dictation)
 without hand-editing config.toml. Preserves the file's comments and ordering,
 automatic backup, one-click daemon restart, and dropdowns for models, keyboard
 layouts and hotkeys. The user-facing interface is in French.
EOF

# --- 6. Scripts de maintenance (rafraîchit les caches) ---------------------
cat > "$ROOT/DEBIAN/postinst" <<'SH'
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -q /usr/share/applications || true
    fi
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -q -f /usr/share/icons/hicolor || true
    fi
fi
exit 0
SH
cp "$ROOT/DEBIAN/postinst" "$ROOT/DEBIAN/postrm"
chmod 755 "$ROOT/DEBIAN/postinst" "$ROOT/DEBIAN/postrm"

# --- 7. Permissions propres (dossiers 755, fichiers 644, exécutables 755) ---
find "$ROOT" -type d -exec chmod 755 {} +
find "$ROOT/usr" -type f -exec chmod 644 {} +
chmod 644 "$ROOT/DEBIAN/control"
chmod 755 "$ROOT/usr/bin/$PKG" "$ROOT/DEBIAN/postinst" "$ROOT/DEBIAN/postrm"

# --- 8. Construction --------------------------------------------------------
say "Construction du .deb"
DEB="$BUILD/${PKG}_${VERSION}-${REVISION}_${ARCH}.deb"
if command -v fakeroot >/dev/null 2>&1; then
    fakeroot dpkg-deb --build "$ROOT" "$DEB" >/dev/null
else
    dpkg-deb --root-owner-group --build "$ROOT" "$DEB" >/dev/null
fi

say "Paquet créé : $DEB"
echo
echo "Installer  :  sudo apt install $DEB"
echo "   (ou     :  sudo dpkg -i $DEB && sudo apt-get -f install)"
echo "Désinstaller :  sudo apt remove $PKG"
