#!/usr/bin/env bash
# Génère un dépôt APT signé, prêt à être servi par GitHub Pages (dossier docs/).
# Régénère tout à chaque nouvelle version : ./build-deb.sh puis ./build-apt-repo.sh
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SRC_DIR"

# Clé de signature (surchargeable : VOXTYPE_APT_GPG_KEY=... ./build-apt-repo.sh)
KEYID="${VOXTYPE_APT_GPG_KEY:-7B73B857273877E7}"
SUITE="stable"
COMP="main"
ARCHES="amd64 arm64 all"
REPO="docs"                       # GitHub Pages sert ce dossier
ORIGIN="voxtype-config-gui"
LABEL="VoxType Config GUI"

say() { printf '\033[1;34m==>\033[0m %s\n' "$1"; }

# --- 1. S'assurer que le .deb existe ---------------------------------------
DEB="$(ls build/voxtype-config_*_all.deb 2>/dev/null | head -1 || true)"
if [ -z "$DEB" ]; then
    say "Aucun .deb trouvé, construction…"
    ./build-deb.sh >/dev/null
    DEB="$(ls build/voxtype-config_*_all.deb | head -1)"
fi
say "Paquet : $DEB"

# --- 2. Arborescence du dépôt ----------------------------------------------
rm -rf "$REPO"
mkdir -p "$REPO/pool/$COMP"
cp "$DEB" "$REPO/pool/$COMP/"
touch "$REPO/.nojekyll"           # empêche GitHub Pages de traiter le site via Jekyll

cd "$REPO"

# --- 3. Index Packages (identique par arch : paquet « all ») ---------------
say "Génération des index Packages"
apt-ftparchive packages pool > /tmp/voxPackages
for arch in $ARCHES; do
    d="dists/$SUITE/$COMP/binary-$arch"
    mkdir -p "$d"
    cp /tmp/voxPackages "$d/Packages"
    gzip -kf "$d/Packages"
done
rm -f /tmp/voxPackages

# --- 4. Fichier Release (checksums de tous les index) ----------------------
say "Génération de Release"
apt-ftparchive \
    -o APT::FTPArchive::Release::Origin="$ORIGIN" \
    -o APT::FTPArchive::Release::Label="$LABEL" \
    -o APT::FTPArchive::Release::Suite="$SUITE" \
    -o APT::FTPArchive::Release::Codename="$SUITE" \
    -o APT::FTPArchive::Release::Architectures="$ARCHES" \
    -o APT::FTPArchive::Release::Components="$COMP" \
    release "dists/$SUITE" > "dists/$SUITE/Release"

# apt-ftparchive n'ajoute pas toujours Date : on le garantit (en-tête en tête de fichier)
if ! grep -q '^Date:' "dists/$SUITE/Release"; then
    DATE_RFC="$(LC_ALL=C date -u '+%a, %d %b %Y %H:%M:%S UTC')"
    sed -i "1i Date: $DATE_RFC" "dists/$SUITE/Release"
fi

# --- 5. Signatures (détachée + inline) -------------------------------------
say "Signature GPG (clé $KEYID)"
gpg --batch --yes --default-key "$KEYID" -abs \
    -o "dists/$SUITE/Release.gpg" "dists/$SUITE/Release"
gpg --batch --yes --default-key "$KEYID" --clearsign \
    -o "dists/$SUITE/InRelease" "dists/$SUITE/Release"

# --- 6. Clé publique à distribuer ------------------------------------------
gpg --armor --export "$KEYID" > KEY.gpg

cd "$SRC_DIR"
say "Dépôt APT prêt dans $REPO/  (à committer puis pousser ; GitHub Pages servira docs/)"
