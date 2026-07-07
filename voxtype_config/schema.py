"""Schéma déclaratif de la configuration VoxType.

Toute l'interface est générée à partir de ces données : ajouter une option
revient à ajouter un Field ici, sans toucher au code de l'UI.

Chemins : chaque Field a un `path` pointé (ex. "output.notification.on_transcription")
qui désigne sa place dans le config.toml.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


# --------------------------------------------------------------------------
# Types de champs
# --------------------------------------------------------------------------

@dataclass
class Field:
    path: str                      # chemin pointé dans le TOML
    label: str                     # titre de la ligne
    kind: str                      # bool|int|float|string|enum|list|path|command
    default: Any = None
    help: str = ""                 # sous-titre explicatif
    options: list[tuple[str, str]] = field(default_factory=list)  # (valeur, libellé) pour enum
    minimum: float = 0
    maximum: float = 100000
    step: float = 1
    placeholder: str = ""
    # pour 'path' : choisir un dossier plutôt qu'un fichier
    pick_folder: bool = False
    # fonction renvoyant des choix dynamiques (valeur, libellé) — ex. périphériques audio
    dynamic_options: Callable[[], list[tuple[str, str]]] | None = None
    # rend ce champ visible seulement si une condition est vraie (path -> valeur attendue)
    depends_on: tuple[str, Any] | None = None


@dataclass
class Group:
    title: str
    fields: list[Field]
    description: str = ""


@dataclass
class Page:
    title: str
    icon: str          # nom d'icône symbolique GNOME
    groups: list[Group]


# --------------------------------------------------------------------------
# Listes de valeurs réutilisées
# --------------------------------------------------------------------------

ENGINES = [
    ("parakeet", "Parakeet (local, NVIDIA NeMo — rapide, multilingue)"),
    ("whisper", "Whisper (local ou distant)"),
    ("moonshine", "Moonshine (local, léger)"),
    ("sensevoice", "SenseVoice"),
    ("paraformer", "Paraformer"),
    ("dolphin", "Dolphin"),
    ("omnilingual", "Omnilingual"),
    ("cohere", "Cohere Transcribe (local, CPU — anglais surtout)"),
    ("soniox", "Soniox (API cloud, temps réel)"),
]

WHISPER_MODELS = [
    ("tiny", "tiny"), ("tiny.en", "tiny.en"),
    ("base", "base"), ("base.en", "base.en"),
    ("small", "small"), ("small.en", "small.en"),
    ("medium", "medium"), ("medium.en", "medium.en"),
    ("large-v3", "large-v3"),
    ("large-v3-turbo", "large-v3-turbo (recommandé GPU)"),
]

ICON_THEMES = [
    ("emoji", "emoji 🎙️"), ("nerd-font", "Nerd Font"), ("material", "Material"),
    ("phosphor", "Phosphor"), ("codicons", "Codicons"), ("omarchy", "Omarchy"),
    ("minimal", "minimal ○●◐×"), ("dots", "dots ◯⬤◔◌"),
    ("arrows", "arrows ▶●↻■"), ("text", "text [MIC][REC]"),
]

OSD_POSITIONS = [
    ("bottom-center", "bas-centre"), ("top-center", "haut-centre"),
    ("bottom-left", "bas-gauche"), ("bottom-right", "bas-droite"),
    ("top-right", "haut-droite"),
]


KNOWN_PARAKEET_MODELS = [
    "parakeet-tdt-0.6b-v3",
    "parakeet-tdt-0.6b-v3-int8",
    "parakeet-tdt-0.6b-v2",
    "parakeet-tdt-0.6b-v2-int8",
    "parakeet-ctc-0.6b",
]


def _parakeet_models() -> list[tuple[str, str]]:
    """Modèles connus + modèles réellement téléchargés dans ~/.local/share/voxtype/models."""
    import os
    found: list[str] = []
    models_dir = os.path.expanduser("~/.local/share/voxtype/models")
    try:
        for name in sorted(os.listdir(models_dir)):
            full = os.path.join(models_dir, name)
            if os.path.isdir(full) and name.startswith("parakeet"):
                found.append(name)
    except OSError:
        pass
    # ordre : modèles installés d'abord (annotés), puis les autres connus
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for m in found:
        out.append((m, f"{m}  ✓ installé"))
        seen.add(m)
    for m in KNOWN_PARAKEET_MODELS:
        if m not in seen:
            out.append((m, m))
            seen.add(m)
    return out or [(m, m) for m in KNOWN_PARAKEET_MODELS]


MODIFIER_KEYS = [
    ("LEFTCTRL", "Ctrl gauche"), ("RIGHTCTRL", "Ctrl droit"),
    ("LEFTSHIFT", "Maj gauche"), ("RIGHTSHIFT", "Maj droite"),
    ("LEFTALT", "Alt gauche"), ("RIGHTALT", "Alt droit (AltGr)"),
    ("LEFTMETA", "Super/Logo gauche"), ("RIGHTMETA", "Super/Logo droit"),
]


def _xkb_layouts() -> list[tuple[str, str]]:
    from . import xkb
    return xkb.layout_options()


def _xkb_variants_current() -> list[tuple[str, str]]:
    """Variantes pour la disposition actuellement configurée (peuplage initial).

    La réactivité au changement de disposition est câblée dans l'app.
    """
    from . import xkb
    from .config_io import ConfigDocument
    try:
        doc = ConfigDocument.load()
        layout = doc.get("output.dotool_xkb_layout", "us") or "us"
    except Exception:
        layout = "us"
    return xkb.variant_options(layout)


def _audio_sources() -> list[tuple[str, str]]:
    """Liste les sources PulseAudio/PipeWire via pactl (rempli dynamiquement)."""
    import subprocess
    out = [("default", "Périphérique système par défaut")]
    try:
        res = subprocess.run(
            ["pactl", "list", "sources", "short"],
            capture_output=True, text=True, timeout=3,
        )
        for line in res.stdout.splitlines():
            cols = line.split("\t")
            if len(cols) >= 2:
                out.append((cols[1], cols[1]))
    except Exception:
        pass
    return out


# --------------------------------------------------------------------------
# Le schéma complet, page par page
# --------------------------------------------------------------------------

SCHEMA: list[Page] = [

    # ---- GÉNÉRAL ----------------------------------------------------------
    Page("Général", "preferences-system-symbolic", [
        Group("Moteur de transcription", [
            Field("engine", "Moteur", "enum", "parakeet", options=ENGINES,
                  help="Moteur utilisé pour convertir la voix en texte."),
        ]),
        Group("Intégration système", [
            Field("state_file", "Fichier d'état", "string", "auto",
                  help="Pour Waybar/polybar. « auto », un chemin, ou « disabled ». "
                       "Requis pour `voxtype record toggle` et `voxtype status`.",
                  placeholder="auto"),
        ]),
    ]),

    # ---- RACCOURCI --------------------------------------------------------
    Page("Raccourci", "input-keyboard-symbolic", [
        Group("Touche d'activation", [
            Field("hotkey.enabled", "Détection intégrée du raccourci", "bool", True,
                  help="⚠️ Si désactivé, la touche de raccourci ne déclenche PLUS rien. "
                       "Ne le désactivez que si vous pilotez VoxType via les raccourcis "
                       "du compositeur (Hyprland, Sway) ou les commandes `voxtype record`."),
            Field("hotkey.key", "Touche", "key", "PAUSE",
                  help="Touche à maintenir (push-to-talk). Cliquez sur « Capturer » "
                       "puis appuyez sur la touche voulue, ou choisissez-en une.",
                  placeholder="PAUSE"),
            Field("hotkey.modifiers", "Modificateurs", "multiselect", [],
                  options=MODIFIER_KEYS,
                  help="Touches à maintenir en plus de la touche principale."),
            Field("hotkey.mode", "Mode d'activation", "enum", "push_to_talk", options=[
                ("push_to_talk", "Push-to-talk (maintenir pour parler)"),
                ("toggle", "Bascule (appuyer pour démarrer/arrêter)"),
            ]),
            Field("hotkey.cancel_key", "Touche d'annulation", "key", "",
                  help="Annule l'enregistrement/transcription en cours. Ex. ESC, F12.",
                  placeholder="ESC"),
            Field("hotkey.model_modifier", "Modificateur modèle secondaire", "enum", "",
                  options=[("", "(aucun)")] + MODIFIER_KEYS,
                  help="Touche de modificateur à maintenir avec le raccourci pour "
                       "utiliser le modèle secondaire au lieu du principal."),
        ]),
    ]),

    # ---- AUDIO ------------------------------------------------------------
    Page("Audio", "audio-input-microphone-symbolic", [
        Group("Entrée", [
            Field("audio.device", "Périphérique d'entrée", "enum", "default",
                  dynamic_options=_audio_sources,
                  help="Micro utilisé pour l'enregistrement."),
            Field("audio.sample_rate", "Fréquence d'échantillonnage (Hz)", "int", 16000,
                  minimum=8000, maximum=48000, step=1000,
                  help="Whisper attend 16000 Hz."),
            Field("audio.max_duration_secs", "Durée max d'enregistrement (s)", "int", 60,
                  minimum=1, maximum=3600, step=5,
                  help="Limite de sécurité."),
            Field("audio.pause_media", "Mettre en pause les médias", "bool", False,
                  help="Met en pause Spotify, Firefox, etc. pendant l'enregistrement "
                       "(nécessite playerctl)."),
        ]),
        Group("Retour sonore", [
            Field("audio.feedback.enabled", "Bips de retour", "bool", False,
                  help="Sons lors du démarrage/arrêt de l'enregistrement."),
            Field("audio.feedback.theme", "Thème sonore", "string", "default",
                  help="« default », « subtle », « mechanical » ou un chemin de dossier.",
                  placeholder="default"),
            Field("audio.feedback.volume", "Volume", "float", 0.7,
                  minimum=0.0, maximum=1.0, step=0.05),
        ]),
    ]),

    # ---- WHISPER ----------------------------------------------------------
    Page("Whisper", "applications-science-symbolic", [
        Group("Modèle", [
            Field("whisper.mode", "Mode d'exécution", "enum", "local", options=[
                ("local", "Local (whisper.cpp, hors-ligne)"),
                ("remote", "Distant (serveur whisper.cpp / API OpenAI)"),
                ("cli", "CLI (binaire whisper externe)"),
            ]),
            Field("whisper.model", "Modèle", "enum", "large-v3-turbo",
                  options=WHISPER_MODELS,
                  help="Les modèles .en sont anglais uniquement, plus rapides. "
                       "large-v3-turbo : rapide avec peu de perte (recommandé GPU)."),
            Field("whisper.language", "Langue", "string", "auto",
                  help="Code à deux lettres (« fr », « en »…), « auto », "
                       "ou liste « en,fr,de » pour l'auto-détection contrainte.",
                  placeholder="fr"),
            Field("whisper.translate", "Traduire vers l'anglais", "bool", False,
                  help="Traduit la parole non-anglaise en anglais dans le transcript."),
            Field("whisper.initial_prompt", "Prompt initial", "string", "",
                  help="Indice de terminologie/noms propres/format. "
                       "Ex. « Discussion technique sur Rust, Kubernetes. »"),
        ]),
        Group("Performance", [
            Field("whisper.threads", "Threads CPU", "int", 0,
                  minimum=0, maximum=128, step=1,
                  help="0 = auto-détection."),
            Field("whisper.flash_attention", "Flash attention", "bool", False,
                  help="Réduit la mémoire (~75 %) et accélère (~10 %) sur CUDA/Vulkan. "
                       "Sans effet sur CPU."),
            Field("whisper.gpu_isolation", "Isolation GPU", "bool", False),
            Field("whisper.gpu_device", "Index GPU", "int", -1,
                  minimum=-1, maximum=16, step=1,
                  help="-1 = automatique. Sur multi-GPU, force un index précis."),
            Field("whisper.on_demand_loading", "Chargement à la demande", "bool", False,
                  help="Libère la mémoire entre les dictées au prix d'une latence au "
                       "premier appui. Utile pour une dictée sporadique."),
        ]),
        Group("Multi-modèles", [
            Field("whisper.secondary_model", "Modèle secondaire", "string", "",
                  help="Pour audio difficile (via model_modifier ou --model).",
                  placeholder="large-v3-turbo"),
            Field("whisper.max_loaded_models", "Modèles max en mémoire", "int", 2,
                  minimum=1, maximum=8, step=1),
            Field("whisper.cold_model_timeout_secs", "Délai de déchargement (s)", "int", 300,
                  minimum=0, maximum=3600, step=30,
                  help="0 = ne jamais décharger automatiquement."),
        ]),
        Group("Serveur distant (mode « remote »)", [
            Field("whisper.remote_endpoint", "URL du serveur", "string", "",
                  placeholder="http://192.168.1.100:8080"),
            Field("whisper.remote_model", "Nom du modèle distant", "string", "whisper-1",
                  placeholder="whisper-1"),
            Field("whisper.remote_api_key", "Clé API", "string", "",
                  help="Ou via la variable VOXTYPE_WHISPER_API_KEY."),
            Field("whisper.remote_timeout_secs", "Timeout (s)", "int", 30,
                  minimum=1, maximum=600, step=5),
        ]),
    ]),

    # ---- PARAKEET ---------------------------------------------------------
    Page("Parakeet", "applications-science-symbolic", [
        Group("Modèle Parakeet", [
            Field("parakeet.model", "Modèle", "enum", "parakeet-tdt-0.6b-v3",
                  dynamic_options=_parakeet_models,
                  help="Modèle Parakeet. « -int8 » = quantifié (plus léger). "
                       "Les modèles marqués ✓ sont déjà téléchargés."),
            Field("parakeet.on_demand_loading", "Chargement à la demande", "bool", False,
                  help="Libère la mémoire entre les dictées (latence au 1er appui)."),
            Field("parakeet.model_type", "Type de modèle", "enum", "", options=[
                ("", "(auto-détecté)"), ("tdt", "tdt"), ("ctc", "ctc")],
                  help="Détecté automatiquement depuis les fichiers du modèle ; "
                       "ne forcez une valeur que si la détection échoue."),
            Field("parakeet.streaming", "Streaming (frappe incrémentale)", "bool", False,
                  help="⚠️ Nécessite un modèle streaming dédié contenant "
                       "tokenizer.model (actuellement parakeet-unified-en-0.6b, "
                       "ANGLAIS uniquement — à télécharger via « voxtype setup "
                       "model »). Avec un modèle standard comme le v3 multilingue, "
                       "le daemon refuse de démarrer. Tape le texte au fil de la "
                       "parole au lieu d'attendre la fin de la dictée."),
        ]),
    ]),

    # ---- SORTIE -----------------------------------------------------------
    Page("Sortie", "text-editor-symbolic", [
        Group("Mode de sortie", [
            Field("output.mode", "Mode", "enum", "type", options=[
                ("type", "Frappe directe (simule le clavier)"),
                ("paste", "Coller (presse-papiers + Ctrl+V)"),
                ("clipboard", "Presse-papiers seul"),
                ("file", "Fichier"),
            ], help="« type » fonctionne partout. « paste » est plus rapide pour les "
                    "longs textes mais le raccourci varie selon l'appli."),
            Field("output.fallback_to_clipboard", "Repli sur presse-papiers", "bool", True,
                  help="Si la frappe échoue, dépose le texte dans le presse-papiers."),
            Field("output.auto_submit", "Valider automatiquement (Entrée)", "bool", False,
                  help="Appuie sur Entrée après la dictée (chats, formulaires)."),
            Field("output.shift_enter_newlines", "Maj+Entrée pour les sauts de ligne", "bool", False,
                  help="Utile pour Cursor, Slack, Discord où Entrée valide."),
            Field("output.append_text", "Texte ajouté après chaque dictée", "string", "",
                  help="Séparateur ajouté avant l'auto-validation. "
                       "Ex. un espace ou « \\n »."),
        ]),
        Group("Pilotes de frappe", [
            Field("output.driver_order", "Ordre des pilotes", "driver_order",
                  ["wtype", "dotool", "ydotool", "clipboard"],
                  options=[
                      ("wtype", "wtype (Wayland, Unicode direct)"),
                      ("dotool", "dotool (uinput + disposition xkb)"),
                      ("ydotool", "ydotool (uinput, daemon requis)"),
                      ("clipboard", "clipboard (repli presse-papiers)"),
                  ],
                  help="Pilotes essayés dans l'ordre jusqu'à ce que l'un réussisse."),
            Field("output.dotool_xkb_layout", "Disposition clavier (dotool)", "enum", "us",
                  dynamic_options=_xkb_layouts,
                  help="Disposition xkb utilisée par dotool pour simuler les touches."),
            Field("output.dotool_xkb_variant", "Variante clavier (dotool)", "enum", "",
                  dynamic_options=_xkb_variants_current,
                  help="⚠️ En français, choisissez « oss » : la variante AZERTY par "
                       "défaut ne peut pas taper les MAJUSCULES accentuées (Ç, É…)."),
            Field("output.type_delay_ms", "Délai entre caractères (ms)", "int", 0,
                  minimum=0, maximum=500, step=5,
                  help="0 = le plus rapide. Augmentez si des caractères sautent."),
            Field("output.pre_type_delay_ms", "Délai avant la frappe (ms)", "int", 0,
                  minimum=0, maximum=1000, step=10,
                  help="Aide certains compositeurs qui perdent le 1er caractère."),
            Field("output.wtype_shift_prefix", "Préfixe Maj (wtype)", "bool", False,
                  help="Contournement pour les apps (Discord) qui perdent le 1er "
                       "caractère CJK."),
            Field("output.wait_for_modifier_release", "Attendre le relâchement des modificateurs",
                  "bool", True,
                  help="Avant de taper, attend que Ctrl/Alt/Maj/Super soient relâchés "
                       "pour éviter de déclencher des raccourcis involontaires."),
            Field("output.modifier_release_timeout_ms", "Délai max d'attente (ms)", "int", 750,
                  minimum=0, maximum=5000, step=50,
                  help="Au-delà de ce délai, la frappe démarre même si un "
                       "modificateur est encore enfoncé."),
        ]),
        Group("Mode coller / presse-papiers", [
            Field("output.paste_keys", "Raccourci de collage", "string", "ctrl+v",
                  help="Ex. ctrl+v, shift+insert, ctrl+shift+v.",
                  placeholder="ctrl+v"),
            Field("output.restore_clipboard", "Restaurer le presse-papiers", "bool", False,
                  help="Restaure le contenu précédent après le collage (mode « paste »)."),
            Field("output.restore_clipboard_delay_ms", "Délai avant restauration (ms)",
                  "int", 200, minimum=0, maximum=2000, step=50),
        ]),
        Group("Sortie fichier (mode « file »)", [
            Field("output.file_path", "Chemin du fichier", "path", "",
                  placeholder="~/dictées.txt"),
            Field("output.file_mode", "Mode d'écriture", "enum", "append", options=[
                ("append", "Ajouter à la fin"),
                ("overwrite", "Écraser"),
            ]),
        ]),
        Group("Hooks de sortie", [
            Field("output.pre_recording_command", "Commande avant enregistrement", "command", "",
                  help="Exécutée avant le début de l'enregistrement."),
            Field("output.pre_output_command", "Commande avant la frappe", "command", "",
                  help="Ex. bloquer les modificateurs : "
                       "`hyprctl dispatch submap voxtype_suppress`"),
            Field("output.post_output_command", "Commande après la frappe", "command", "",
                  help="Ex. `hyprctl dispatch submap reset`"),
        ]),
        Group("Post-traitement", [
            Field("output.post_process.command", "Commande de post-traitement", "command", "",
                  help="Le transcript passe par stdin, la sortie stdout est tapée. "
                       "Ex. nettoyage LLM (Ollama), suppression de mots de remplissage."),
            Field("output.post_process.timeout_ms", "Timeout (ms)", "int", 30000,
                  minimum=100, maximum=120000, step=1000),
            Field("output.post_process.trim", "Supprimer les espaces en bord", "bool", True),
            Field("output.post_process.fallback_on_empty", "Repli si sortie vide", "bool", True,
                  help="Utilise le texte original si la commande renvoie du vide."),
        ]),
    ]),

    # ---- NOTIFICATIONS ----------------------------------------------------
    Page("Notifications", "preferences-system-notifications-symbolic", [
        Group("Notifications de bureau", [
            Field("output.notification.on_recording_start", "Au démarrage de l'enregistrement",
                  "bool", False),
            Field("output.notification.on_recording_stop", "À l'arrêt de l'enregistrement",
                  "bool", False),
            Field("output.notification.on_transcription", "À la fin de la transcription",
                  "bool", False, help="Affiche le texte transcrit."),
            Field("output.notification.show_engine_icon", "Afficher l'icône du moteur",
                  "bool", False),
        ]),
    ]),

    # ---- TEXTE ------------------------------------------------------------
    Page("Texte", "format-text-rich-symbolic", [
        Group("Traitement du texte", [
            Field("text.spoken_punctuation", "Ponctuation dictée", "bool", False,
                  help="Dire « point » insère « . », etc."),
            Field("text.smart_auto_submit", "Auto-validation intelligente", "bool", False,
                  help="Dire « submit » en fin de dictée appuie sur Entrée "
                       "(le mot est retiré du texte)."),
            Field("text.filter_filler_words", "Filtrer les mots de remplissage", "bool", True,
                  help="Retire « euh », « um », etc."),
            Field("text.filler_words", "Mots de remplissage", "list",
                  ["uh", "um", "er", "ah", "eh", "hmm", "hm", "mm", "mhm"],
                  help="Liste séparée par des virgules.",
                  placeholder="euh, hum, ben"),
        ]),
        Group("Remplacements", [
            # Champ spécial : éditeur clé→valeur dédié (géré par un widget custom).
            Field("text.replacements", "Remplacements de mots", "replacements", {},
                  help="Remplacements automatiques, insensibles à la casse. "
                       "Ex. « vox type » → « voxtype »."),
        ]),
    ]),

    # ---- VAD --------------------------------------------------------------
    Page("Détection de voix", "audio-volume-high-symbolic", [
        Group("Voice Activity Detection", [
            Field("vad.enabled", "Activer la VAD", "bool", False,
                  help="Filtre les enregistrements silencieux (évite les "
                       "hallucinations de Whisper)."),
            Field("vad.backend", "Backend", "enum", "auto", options=[
                ("auto", "auto"), ("energy", "energy"), ("whisper", "whisper"),
            ]),
            Field("vad.threshold", "Seuil de détection", "float", 0.5,
                  minimum=0.0, maximum=1.0, step=0.05,
                  help="0.0 = sensible, 1.0 = agressif."),
            Field("vad.min_speech_duration_ms", "Durée min de parole (ms)", "int", 100,
                  minimum=0, maximum=5000, step=50),
        ]),
    ]),

    # ---- AFFICHAGE (OSD + statut) -----------------------------------------
    Page("Affichage", "video-display-symbolic", [
        Group("On-Screen Display (OSD)", [
            Field("osd.enabled", "Activer l'OSD", "bool", False,
                  help="Affichage à l'écran de l'état et de la forme d'onde."),
            Field("osd.frontend", "Frontend", "enum", "gtk4", options=[
                ("gtk4", "GTK4"), ("quickshell", "Quickshell"), ("native", "Natif"),
            ]),
            Field("osd.position", "Position", "enum", "bottom-center", options=OSD_POSITIONS),
            Field("osd.width_px", "Largeur (px)", "int", 400, minimum=100, maximum=2000, step=10),
            Field("osd.height_px", "Hauteur (px)", "int", 48, minimum=20, maximum=400, step=4),
            Field("osd.margin_px", "Marge (px)", "int", 24, minimum=0, maximum=400, step=4),
            Field("osd.opacity", "Opacité", "float", 1.0, minimum=0.0, maximum=1.0, step=0.05),
            Field("osd.waveform_gain", "Gain de la forme d'onde", "float", 10.0,
                  minimum=0.0, maximum=100.0, step=1.0),
        ]),
        Group("Icône de statut (Waybar/tray)", [
            Field("status.icon_theme", "Thème d'icônes", "enum", "emoji", options=ICON_THEMES),
            Field("status.urgency", "Urgence des notifications", "enum", "normal", options=[
                ("low", "low (sans bannière sur GNOME)"),
                ("normal", "normal"),
                ("critical", "critical"),
            ]),
        ]),
    ]),

    # ---- RÉUNION ----------------------------------------------------------
    Page("Réunion", "system-users-symbolic", [
        Group("Mode réunion", [
            Field("meeting.enabled", "Activer le mode réunion", "bool", False),
        ]),
        Group("Audio de réunion", [
            Field("meeting.audio.source", "Source audio", "enum", "mic", options=[
                ("mic", "Micro seul"),
                ("loopback", "Sortie système (loopback)"),
                ("both", "Les deux"),
            ]),
        ]),
        Group("Diarisation (qui parle)", [
            Field("meeting.diarization.enabled", "Activer la diarisation", "bool", False,
                  help="Identifie les différents locuteurs."),
        ]),
    ]),

    # ---- PROFILS ----------------------------------------------------------
    Page("Profils", "avatar-default-symbolic", [
        Group("Profils de dictée", [
            # Champ spécial : éditeur de tables [profiles.<nom>] (widget dédié).
            Field("profiles", "Profils", "profiles", {},
                  help="Profils nommés de post-traitement. Les options non "
                       "renseignées héritent de la configuration principale."),
        ], description="Utilisés via « voxtype record start --profile <nom> » ou "
                       "via un modificateur associé ci-dessous."),
        Group("Modificateur → profil", [
            Field("hotkey.profile_modifiers", "Associations modificateur → profil",
                  "replacements", {},
                  help="Maintenez ce modificateur avec la touche de dictée pour "
                       "activer le profil. Clé : un modificateur (LEFTSHIFT, "
                       "RIGHTCTRL, LEFTALT…), valeur : le nom du profil. "
                       "Nécessite la détection intégrée du raccourci."),
        ]),
    ]),
]


def all_fields() -> list[Field]:
    return [f for page in SCHEMA for g in page.groups for f in g.fields]
