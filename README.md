# VoxType Configuration — graphical editor

A **GTK4 / libadwaita** application to configure
[VoxType](https://github.com/) entirely through a graphical interface, without
hand-editing `config.toml`.

![capture](data/earth.tyler.VoxTypeConfig.svg)

## Features

- **Full coverage** of the VoxType configuration schema, organized in pages:
  General, Hotkey, Audio, Whisper, Parakeet, Output, Notifications, Text,
  Voice Detection (VAD), Display (OSD + status), Meeting.
- **Preserves your comments and ordering**: only the values you change are
  rewritten (via [`tomlkit`](https://github.com/sdispater/tomlkit)).
- **Automatic backup** (`config.toml.bak`) on every save.
- **One-click daemon restart** (`systemctl --user restart voxtype`).
- **TOML preview** before saving.
- Dynamic detection of **audio devices** (via `pactl`).
- Dedicated editor for **word replacements** (key → value).
- Does not write default values: the file stays minimal and readable.

## Installation (Debian/Ubuntu)

### Recommended: APT repository (signed, automatic updates)

Add the repository and its signing key once:

```bash
sudo install -d /etc/apt/keyrings
curl -fsSL https://belenos-toutatis.github.io/voxtype-config-gui/KEY.gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/voxtype-config.gpg
echo "deb [signed-by=/etc/apt/keyrings/voxtype-config.gpg] https://belenos-toutatis.github.io/voxtype-config-gui stable main" \
  | sudo tee /etc/apt/sources.list.d/voxtype-config.list
sudo apt update
sudo apt install voxtype-config
```

Because the repository is signed and declared as a trusted source, **no
"third-party package" warning** appears, and new versions arrive via
`sudo apt upgrade`.

### Alternative: direct `.deb`

```bash
sudo apt install ./build/voxtype-config_*_all.deb
```

> Installed this way from GNOME Software, a "third-party package" banner shows
> (normal for any `.deb` outside a repository). Installing from the terminal
> as above does not show it.

### Run / uninstall

```bash
voxtype-config                 # or "VoxType Configuration" in your applications
sudo apt remove voxtype-config
```

> Your `~/.config/voxtype/config.toml` is never touched by uninstalling.

## Releasing a new version (maintainer)

```bash
# 1. (optional) bump the version in build-deb.sh
./build-deb.sh            # builds build/voxtype-config_<ver>_all.deb
./build-apt-repo.sh       # regenerates and signs the APT repository in docs/
git add -A && git commit -m "release <ver>" && git push
```

GitHub Pages serves the `docs/` directory. Signing uses the GPG key
`VoxType Config GUI APT` (fingerprint `D7464FE0D891102553AFC9CA7B73B857273877E7`);
the **private** key stays in the local keyring, only the public key
(`docs/KEY.gpg`) is published.

## Development / running without installing

GTK bindings come from the system; only `tomlkit` is a Python package.

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/pip install tomlkit
PYTHONPATH=. .venv/bin/python -m voxtype_config
```

You can target another config file:

```bash
PYTHONPATH=. .venv/bin/python -m voxtype_config /path/to/config.toml
```

## Architecture

| File | Role |
|---|---|
| `voxtype_config/schema.py` | Declarative description of **all** options. Adding a setting = adding a `Field` here. |
| `voxtype_config/widgets.py` | Generates the libadwaita rows from the schema (get/set per type). |
| `voxtype_config/config_io.py` | TOML read/write by dotted path, preserving formatting. |
| `voxtype_config/app.py` | Window, navigation, saving, daemon restart. |
| `voxtype_config/system.py` | systemd interactions / VoxType detection. |

Because the UI is generated from the schema, following a new VoxType option
only requires one line in `schema.py`.
