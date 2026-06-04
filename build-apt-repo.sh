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

# --- 3b. Catalogue AppStream DEP-11 (fiche propre dans le Centre d'applications)
APP_ID="earth.tyler.VoxTypeConfig"
if command -v appstreamcli >/dev/null 2>&1 \
   && appstreamcli compose --version >/dev/null 2>&1; then
    say "Génération du catalogue AppStream DEP-11"
    DEP11="dists/$SUITE/$COMP/dep11"
    mkdir -p "$DEP11"
    TREE="$(mktemp -d)"; ASOUT="$(mktemp -d)"
    dpkg-deb -x "$SRC_DIR/$DEB" "$TREE"
    appstreamcli compose --origin "$ORIGIN" \
        --result-root "$ASOUT" --data-dir "$ASOUT/data" \
        --icons-dir "$ASOUT/icons" --prefix /usr --no-net \
        --print-report on-error "$TREE" >/dev/null 2>&1 || true

    # Icônes : un tarball par taille, fichier nommé <paquet>_<Icon>.png
    ICONNAME="voxtype-config_${APP_ID}.png"
    for size in 48x48 64x64 64x64@2 128x128 128x128@2; do
        src="$ASOUT/icons/$size/$APP_ID.png"
        [ -f "$src" ] || continue
        td="$(mktemp -d)"; cp "$src" "$td/$ICONNAME"
        tar -C "$td" -czf "$DEP11/icons-$size.tar.gz" "$ICONNAME"
        rm -rf "$td"
    done

    # Catalogue Components-<arch>.yml.gz (émis en JSON, qui est du YAML valide)
    python3 - "$DEP11" "$ORIGIN" "$APP_ID" "$ICONNAME" <<'PY'
import json, sys, gzip, os
dep11, origin, appid, iconname = sys.argv[1:5]
header = {"File": "DEP-11", "Version": "1.0", "Origin": origin}
comp = {
    "Type": "desktop-application", "ID": appid, "Package": "voxtype-config",
    "ProjectLicense": "MIT",
    "Name": {"C": "Configuration VoxType", "en": "VoxType Settings"},
    "Summary": {"C": "Configurer la dictée vocale VoxType",
                "en": "Configure VoxType voice dictation"},
    "Description": {
        "C": ("<p>Interface graphique GTK4 / libadwaita pour configurer "
              "entièrement VoxType (dictée vocale) sans éditer le fichier "
              "config.toml à la main.</p><ul>"
              "<li>Couverture complète des réglages, organisée par pages</li>"
              "<li>Préserve les commentaires et l'ordre du fichier</li>"
              "<li>Sauvegarde automatique et redémarrage du daemon en un clic</li>"
              "<li>Listes déroulantes : modèles, dispositions clavier, raccourcis</li>"
              "<li>Tableau trié pour les remplacements de mots</li></ul>"),
        "en": ("<p>A GTK4 / libadwaita interface to fully configure VoxType "
               "(voice dictation) without hand-editing config.toml.</p><ul>"
               "<li>Complete coverage of the settings, organised by pages</li>"
               "<li>Preserves the comments and ordering of the file</li>"
               "<li>Automatic backup and one-click daemon restart</li>"
               "<li>Dropdowns for models, keyboard layouts and hotkeys</li>"
               "<li>Sorted table for word replacements</li></ul>"),
    },
    "Developer": {"name": {"C": "Emmanuel Wenner"}},
    "Categories": ["Utility", "Settings"],
    "Keywords": {"C": ["voxtype", "dictée", "voix", "transcription"]},
    "Url": {"homepage": "https://github.com/Belenos-Toutatis/voxtype-config-gui",
            "bugtracker": "https://github.com/Belenos-Toutatis/voxtype-config-gui/issues"},
    "Launchable": {"desktop-id": [appid + ".desktop"]},
    "Icon": {"cached": [
        {"name": iconname, "width": 48, "height": 48},
        {"name": iconname, "width": 64, "height": 64},
        {"name": iconname, "width": 128, "height": 128},
    ]},
}
doc = ("---\n" + json.dumps(header, ensure_ascii=False)
       + "\n---\n" + json.dumps(comp, ensure_ascii=False) + "\n").encode("utf-8")
for arch in ("amd64", "arm64"):
    with gzip.open(os.path.join(dep11, f"Components-{arch}.yml.gz"), "wb") as fh:
        fh.write(doc)
PY
    rm -rf "$TREE" "$ASOUT"
else
    say "appstreamcli compose absent — DEP-11 ignoré (dépôt fonctionnel quand même)"
fi

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
