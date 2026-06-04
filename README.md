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

## Installation (paquet .deb, Debian/Ubuntu)

```bash
./build-deb.sh
sudo apt install ./build/voxtype-config_0.1.0-1_all.deb
```

apt résout automatiquement les dépendances (`python3-gi`, `gir1.2-gtk-4.0`,
`gir1.2-adw-1`, `python3-tomlkit`, `python3-evdev`). L'application s'installe
dans `/usr/share/voxtype-config`, avec le lanceur `/usr/bin/voxtype-config` et
l'entrée de menu « Configuration VoxType ».

Puis lancez :

```bash
voxtype-config
```

ou cherchez **Configuration VoxType** dans vos applications.

Désinstallation propre :

```bash
sudo apt remove voxtype-config
```

> Votre `~/.config/voxtype/config.toml` n'est jamais touché par la
> désinstallation.

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
