# Configuration VoxType — éditeur graphique

Une application **GTK4 / libadwaita** pour configurer entièrement
[VoxType](https://github.com/) via une interface graphique, sans éditer le
`config.toml` à la main.

![capture](data/earth.tyler.VoxTypeConfig.svg)

## Fonctionnalités

- **Couverture complète** du schéma de configuration VoxType, organisé en pages :
  Général, Raccourci, Audio, Whisper, Parakeet, Sortie, Notifications, Texte,
  Détection de voix (VAD), Affichage (OSD + statut), Réunion.
- **Préserve vos commentaires et l'ordre** du fichier : seules les valeurs
  modifiées sont réécrites (via [`tomlkit`](https://github.com/sdispater/tomlkit)).
- **Sauvegarde automatique** (`config.toml.bak`) à chaque enregistrement.
- **Redémarrage du daemon** en un clic (`systemctl --user restart voxtype`).
- **Aperçu du TOML** avant d'enregistrer.
- Détection dynamique des **périphériques audio** (via `pactl`).
- Éditeur dédié pour les **remplacements de mots** (clé → valeur).
- N'écrit pas les valeurs par défaut : le fichier reste minimal et lisible.

## Installation (Debian/Ubuntu)

### Recommandé : dépôt APT (signé, mises à jour automatiques)

Une seule fois, on ajoute le dépôt et sa clé de signature :

```bash
sudo install -d /etc/apt/keyrings
curl -fsSL https://belenos-toutatis.github.io/voxtype-config-gui/KEY.gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/voxtype-config.gpg
echo "deb [signed-by=/etc/apt/keyrings/voxtype-config.gpg] https://belenos-toutatis.github.io/voxtype-config-gui stable main" \
  | sudo tee /etc/apt/sources.list.d/voxtype-config.list
sudo apt update
sudo apt install voxtype-config
```

Le dépôt étant signé et déclaré comme source de confiance, **aucun avertissement
« paquet tiers »** n'apparaît, et les nouvelles versions arrivent via
`sudo apt upgrade`.

### Alternative : `.deb` direct

```bash
sudo apt install ./build/voxtype-config_*_all.deb
```

> Installé par cette voie via le Centre d'applications GNOME, un bandeau
> « paquet tiers » s'affiche (normal pour tout `.deb` hors dépôt). L'installation
> en terminal ci-dessus ne l'affiche pas.

### Lancer / désinstaller

```bash
voxtype-config                 # ou « Configuration VoxType » dans vos applications
sudo apt remove voxtype-config
```

> Votre `~/.config/voxtype/config.toml` n'est jamais touché par la
> désinstallation.

## Publier une nouvelle version (mainteneur)

```bash
# 1. (optionnel) bump de version dans build-deb.sh
./build-deb.sh            # construit build/voxtype-config_<ver>_all.deb
./build-apt-repo.sh       # régénère et signe le dépôt APT dans docs/
git add -A && git commit -m "release <ver>" && git push
```

GitHub Pages sert le dossier `docs/`. La signature utilise la clé GPG
`VoxType Config GUI APT` (empreinte `D7464FE0D891102553AFC9CA7B73B857273877E7`) ;
la clé **privée** reste dans le trousseau local, seule la clé publique
(`docs/KEY.gpg`) est publiée.

## Développement / exécution sans installer

Les liaisons GTK proviennent du système ; seul `tomlkit` est un paquet Python.

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install tomlkit
PYTHONPATH=. .venv/bin/python -m voxtype_config
```

On peut viser un autre fichier de config :

```bash
PYTHONPATH=. .venv/bin/python -m voxtype_config /chemin/vers/config.toml
```

## Architecture

| Fichier | Rôle |
|---|---|
| `voxtype_config/schema.py` | Description déclarative de **toutes** les options. Ajouter un réglage = ajouter un `Field` ici. |
| `voxtype_config/widgets.py` | Génère les lignes libadwaita depuis le schéma (get/set par type). |
| `voxtype_config/config_io.py` | Lecture/écriture TOML par chemin pointé, en préservant la mise en forme. |
| `voxtype_config/app.py` | Fenêtre, navigation, sauvegarde, redémarrage du daemon. |
| `voxtype_config/system.py` | Interactions systemd / détection de VoxType. |

L'UI étant générée à partir du schéma, suivre une nouvelle option de VoxType ne
demande qu'une ligne dans `schema.py`.
