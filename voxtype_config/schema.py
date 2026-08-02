"""Declarative schema for the VoxType configuration.

The whole UI is generated from this data: adding an option amounts to
adding a Field here, without touching the UI code.

Paths: each Field has a `path` (e.g. "output.notification.on_transcription")
pointing to its place in config.toml.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


# --------------------------------------------------------------------------
# Field types
# --------------------------------------------------------------------------

@dataclass
class Field:
    path: str                      # path pointed to in the TOML
    label: str                     # row title
    kind: str                      # bool|int|float|string|enum|list|path|command
    default: Any = None
    help: str = ""                 # explanatory subtitle
    options: list[tuple[str, str]] = field(default_factory=list)  # (value, label) for enum
    minimum: float = 0
    maximum: float = 100000
    step: float = 1
    placeholder: str = ""
    # for 'path': choose a folder instead of a file
    pick_folder: bool = False
    # function returning dynamic choices (value, label) — e.g. audio devices
    dynamic_options: Callable[[], list[tuple[str, str]]] | None = None
    # makes this field visible only if a condition holds (path -> expected value)
    depends_on: tuple[str, Any] | None = None


@dataclass
class Group:
    title: str
    fields: list[Field]
    description: str = ""


@dataclass
class Page:
    title: str
    icon: str          # GNOME symbolic icon name
    groups: list[Group]


# --------------------------------------------------------------------------
# Reused value lists
# --------------------------------------------------------------------------

ENGINES = [
    ("parakeet", "Parakeet (local, NVIDIA NeMo — fast, multilingual)"),
    ("whisper", "Whisper (local or remote)"),
    ("moonshine", "Moonshine (local, lightweight)"),
    ("sensevoice", "SenseVoice"),
    ("paraformer", "Paraformer"),
    ("dolphin", "Dolphin"),
    ("omnilingual", "Omnilingual"),
    ("cohere", "Cohere Transcribe (local, CPU — English mainly)"),
    ("soniox", "Soniox (cloud API, real-time)"),
]

WHISPER_MODELS = [
    ("tiny", "tiny"), ("tiny.en", "tiny.en"),
    ("base", "base"), ("base.en", "base.en"),
    ("small", "small"), ("small.en", "small.en"),
    ("medium", "medium"), ("medium.en", "medium.en"),
    ("large-v3", "large-v3"),
    ("large-v3-turbo", "large-v3-turbo (GPU recommended)"),
]

ICON_THEMES = [
    ("emoji", "emoji 🎙️"), ("nerd-font", "Nerd Font"), ("material", "Material"),
    ("phosphor", "Phosphor"), ("codicons", "Codicons"), ("omarchy", "Omarchy"),
    ("minimal", "minimal ○●◐×"), ("dots", "dots ◯⬤◔◌"),
    ("arrows", "arrows ▶●↻■"), ("text", "text [MIC][REC]"),
]

OSD_POSITIONS = [
    ("bottom-center", "bottom center"), ("top-center", "top center"),
    ("bottom-left", "bottom left"), ("bottom-right", "bottom right"),
    ("top-right", "top right"),
]


KNOWN_PARAKEET_MODELS = [
    "parakeet-tdt-0.6b-v3",
    "parakeet-tdt-0.6b-v3-int8",
    "parakeet-tdt-0.6b-v2",
    "parakeet-tdt-0.6b-v2-int8",
    "parakeet-ctc-0.6b",
]


def _parakeet_models() -> list[tuple[str, str]]:
    """Known models + models actually downloaded in ~/.local/share/voxtype/models."""
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
    # order: installed models first (annotated), then the other known ones
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for m in found:
        out.append((m, f"{m}  ✓ installed"))
        seen.add(m)
    for m in KNOWN_PARAKEET_MODELS:
        if m not in seen:
            out.append((m, m))
            seen.add(m)
    return out or [(m, m) for m in KNOWN_PARAKEET_MODELS]


MODIFIER_KEYS = [
    ("LEFTCTRL", "Left Ctrl"), ("RIGHTCTRL", "Right Ctrl"),
    ("LEFTSHIFT", "Left Shift"), ("RIGHTSHIFT", "Right Shift"),
    ("LEFTALT", "Left Alt"), ("RIGHTALT", "Right Alt (AltGr)"),
    ("LEFTMETA", "Left Super/Logo"), ("RIGHTMETA", "Right Super/Logo"),
]


def _xkb_layouts() -> list[tuple[str, str]]:
    from . import xkb
    return xkb.layout_options()


def _xkb_variants_current() -> list[tuple[str, str]]:
    """Variants for the currently configured layout (initial population).

    Reactivity to layout changes is wired up in the app.
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
    """Lists PulseAudio/PipeWire sources via pactl (filled dynamically)."""
    import subprocess
    out = [("default", "System default device")]
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
# The complete schema, page by page
# --------------------------------------------------------------------------

SCHEMA: list[Page] = [

    # ---- GENERAL ---------------------------------------------------------
    Page("General", "preferences-system-symbolic", [
        Group("Transcription engine", [
            Field("engine", "Engine", "enum", "parakeet", options=ENGINES,
                  help="Engine used to convert speech to text."),
        ]),
        Group("System integration", [
            Field("state_file", "State file", "string", "auto",
                  help="For Waybar/polybar. 'auto', a path, or 'disabled'. "
                       "Required for `voxtype record toggle` and `voxtype status`.",
                  placeholder="auto"),
        ]),
    ]),

    # ---- HOTKEY ----------------------------------------------------------
    Page("Hotkey", "input-keyboard-symbolic", [
        Group("Activation key", [
            Field("hotkey.enabled", "Built-in hotkey detection", "bool", True,
                  help="⚠️ If disabled, the hotkey no longer triggers ANYTHING. "
                       "Only disable it if you drive VoxType via compositor "
                       "shortcuts (Hyprland, Sway) or the `voxtype record` commands."),
            Field("hotkey.key", "Key", "key", "PAUSE",
                  help="Key to hold (push-to-talk). Click 'Capture' then press "
                       "the desired key, or pick one from the list.",
                  placeholder="PAUSE"),
            Field("hotkey.modifiers", "Modifiers", "multiselect", [],
                  options=MODIFIER_KEYS,
                  help="Keys to hold in addition to the main key."),
            Field("hotkey.mode", "Activation mode", "enum", "push_to_talk", options=[
                ("push_to_talk", "Push-to-talk (hold to talk)"),
                ("toggle", "Toggle (press to start/stop)"),
            ]),
            Field("hotkey.cancel_key", "Cancel key", "key", "",
                  help="Cancels the current recording/transcription. E.g. ESC, F12.",
                  placeholder="ESC"),
            Field("hotkey.model_modifier", "Secondary-model modifier", "enum", "",
                  options=[("", "(none)")] + MODIFIER_KEYS,
                  help="Modifier key to hold with the hotkey to use the "
                       "secondary model instead of the main one."),
        ]),
    ]),

    # ---- AUDIO -----------------------------------------------------------
    Page("Audio", "audio-input-microphone-symbolic", [
        Group("Input", [
            Field("audio.device", "Input device", "enum", "default",
                  dynamic_options=_audio_sources,
                  help="Microphone used for recording."),
            Field("audio.sample_rate", "Sample rate (Hz)", "int", 16000,
                  minimum=8000, maximum=48000, step=1000,
                  help="Whisper expects 16000 Hz."),
            Field("audio.max_duration_secs", "Max recording duration (s)", "int", 60,
                  minimum=1, maximum=3600, step=5,
                  help="Safety limit."),
            Field("audio.pause_media", "Pause media players", "bool", False,
                  help="Pauses Spotify, Firefox, etc. during recording "
                       "(requires playerctl)."),
        ]),
        Group("Audio feedback", [
            Field("audio.feedback.enabled", "Feedback beeps", "bool", False,
                  help="Sounds on recording start/stop."),
            Field("audio.feedback.theme", "Sound theme", "string", "default",
                  help="'default', 'subtle', 'mechanical', or a folder path.",
                  placeholder="default"),
            Field("audio.feedback.volume", "Volume", "float", 0.7,
                  minimum=0.0, maximum=1.0, step=0.05),
        ]),
    ]),

    # ---- WHISPER ---------------------------------------------------------
    Page("Whisper", "applications-science-symbolic", [
        Group("Model", [
            Field("whisper.mode", "Execution mode", "enum", "local", options=[
                ("local", "Local (whisper.cpp, offline)"),
                ("remote", "Remote (whisper.cpp server / OpenAI API)"),
                ("cli", "CLI (external whisper binary)"),
            ]),
            Field("whisper.model", "Model", "enum", "large-v3-turbo",
                  options=WHISPER_MODELS,
                  help="The .en models are English-only and faster. "
                       "large-v3-turbo: fast with little loss (GPU recommended)."),
            Field("whisper.language", "Language", "string", "auto",
                  help="Two-letter code ('fr', 'en'…), 'auto', or a list like "
                       "'en,fr,de' for constrained auto-detection.",
                  placeholder="fr"),
            Field("whisper.translate", "Translate to English", "bool", False,
                  help="Translates non-English speech into English in the transcript."),
            Field("whisper.initial_prompt", "Initial prompt", "string", "",
                  help="Hint for terminology/proper nouns/format. "
                       "E.g. 'Technical discussion about Rust, Kubernetes.'"),
        ]),
        Group("Performance", [
            Field("whisper.threads", "CPU threads", "int", 0,
                  minimum=0, maximum=128, step=1,
                  help="0 = auto-detection."),
            Field("whisper.flash_attention", "Flash attention", "bool", False,
                  help="Reduces memory (~75 %) and speeds up (~10 %) on CUDA/Vulkan. "
                       "No effect on CPU."),
            Field("whisper.gpu_isolation", "GPU isolation", "bool", False),
            Field("whisper.gpu_device", "GPU index", "int", -1,
                  minimum=-1, maximum=16, step=1,
                  help="-1 = automatic. On multi-GPU, forces a specific index."),
            Field("whisper.on_demand_loading", "On-demand loading", "bool", False,
                  help="Frees memory between dictations at the cost of latency on "
                       "the first press. Useful for occasional dictation."),
        ]),
        Group("Multi-model", [
            Field("whisper.secondary_model", "Secondary model", "string", "",
                  help="For difficult audio (via model_modifier or --model).",
                  placeholder="large-v3-turbo"),
            Field("whisper.max_loaded_models", "Max models in memory", "int", 2,
                  minimum=1, maximum=8, step=1),
            Field("whisper.cold_model_timeout_secs", "Unload delay (s)", "int", 300,
                  minimum=0, maximum=3600, step=30,
                  help="0 = never unload automatically."),
        ]),
        Group("Remote server (remote mode)", [
            Field("whisper.remote_endpoint", "Server URL", "string", "",
                  placeholder="http://192.168.1.100:8080"),
            Field("whisper.remote_model", "Remote model name", "string", "whisper-1",
                  placeholder="whisper-1"),
            Field("whisper.remote_api_key", "API key", "string", "",
                  help="Or via the VOXTYPE_WHISPER_API_KEY variable."),
            Field("whisper.remote_timeout_secs", "Timeout (s)", "int", 30,
                  minimum=1, maximum=600, step=5),
        ]),
    ]),

    # ---- PARAKEET --------------------------------------------------------
    Page("Parakeet", "applications-science-symbolic", [
        Group("Parakeet model", [
            Field("parakeet.model", "Model", "enum", "parakeet-tdt-0.6b-v3",
                  dynamic_options=_parakeet_models,
                  help="Parakeet model. '-int8' = quantized (lighter). "
                       "Models marked ✓ are already downloaded."),
            Field("parakeet.on_demand_loading", "On-demand loading", "bool", False,
                  help="Frees memory between dictations (latency on the first press)."),
            Field("parakeet.model_type", "Model type", "enum", "", options=[
                ("", "(auto-detected)"), ("tdt", "tdt"), ("ctc", "ctc")],
                  help="Detected automatically from the model files; only force "
                       "a value if detection fails."),
            Field("parakeet.streaming", "Streaming (incremental typing)", "bool", False,
                  help="⚠️ Requires a dedicated streaming model containing "
                       "tokenizer.model (currently parakeet-unified-en-0.6b, "
                       "ENGLISH only — download via 'voxtype setup model'). "
                       "With a standard model like the multilingual v3, the "
                       "daemon refuses to start. Types text as you speak "
                       "instead of waiting for the end of the dictation."),
        ]),
    ]),

    # ---- OUTPUT ----------------------------------------------------------
    Page("Output", "text-editor-symbolic", [
        Group("Output mode", [
            Field("output.mode", "Mode", "enum", "type", options=[
                ("type", "Direct typing (simulates keyboard)"),
                ("paste", "Paste (clipboard + Ctrl+V)"),
                ("clipboard", "Clipboard only"),
                ("file", "File"),
            ], help="'type' works everywhere. 'paste' is faster for long texts, "
                    "but the shortcut varies by app."),
            Field("output.fallback_to_clipboard", "Clipboard fallback", "bool", True,
                  help="If typing fails, drops the text into the clipboard."),
            Field("output.auto_submit", "Auto-submit (Enter)", "bool", False,
                  help="Presses Enter after dictation (chats, forms)."),
            Field("output.shift_enter_newlines", "Shift+Enter for newlines", "bool", False,
                  help="Useful for Cursor, Slack, Discord where Enter submits."),
            Field("output.append_text", "Text appended after each dictation", "enum", "",
                  options=[
                      ("", "(none)"),
                      (" ", "Space"),
                      ("\n", "New line"),
                  ],
                  help="Separator appended at the end of each dictation (before "
                       "auto-submit). A space prevents two consecutive dictations "
                       "from sticking together. A custom value typed by hand in "
                       "the file is preserved."),
        ]),
        Group("Typing drivers", [
            Field("output.driver_order", "Driver order", "driver_order",
                  ["wtype", "dotool", "ydotool", "clipboard"],
                  options=[
                      ("wtype", "wtype (Wayland, direct Unicode)"),
                      ("dotool", "dotool (uinput + xkb layout)"),
                      ("ydotool", "ydotool (uinput, daemon required)"),
                      ("clipboard", "clipboard (clipboard fallback)"),
                  ],
                  help="Drivers tried in order until one succeeds."),
            Field("output.dotool_xkb_layout", "Keyboard layout (dotool)", "enum", "us",
                  dynamic_options=_xkb_layouts,
                  help="xkb layout used by dotool to simulate keys."),
            Field("output.dotool_xkb_variant", "Keyboard variant (dotool)", "enum", "",
                  dynamic_options=_xkb_variants_current,
                  help="⚠️ For French, choose 'oss': the default AZERTY variant "
                       "cannot type accented uppercase letters (Ç, É…)."),
            Field("output.type_delay_ms", "Delay between characters (ms)", "int", 0,
                  minimum=0, maximum=500, step=5,
                  help="0 = fastest. Increase if characters get dropped."),
            Field("output.pre_type_delay_ms", "Delay before typing (ms)", "int", 0,
                  minimum=0, maximum=1000, step=10,
                  help="Helps some compositors that drop the 1st character."),
            Field("output.wtype_shift_prefix", "Shift prefix (wtype)", "bool", False,
                  help="Workaround for apps (Discord) that drop the 1st "
                       "CJK character."),
            Field("output.wait_for_modifier_release", "Wait for modifier release",
                  "bool", True,
                  help="Before typing, waits for Ctrl/Alt/Shift/Super to be "
                       "released to avoid triggering unintended shortcuts."),
            Field("output.modifier_release_timeout_ms", "Max wait delay (ms)", "int", 750,
                  minimum=0, maximum=5000, step=50,
                  help="Past this delay, typing starts even if a modifier is "
                       "still held."),
        ]),
        Group("Paste / clipboard mode", [
            Field("output.paste_keys", "Paste shortcut", "string", "ctrl+v",
                  help="E.g. ctrl+v, shift+insert, ctrl+shift+v.",
                  placeholder="ctrl+v"),
            Field("output.restore_clipboard", "Restore clipboard", "bool", False,
                  help="Restores the previous content after pasting (paste mode)."),
            Field("output.restore_clipboard_delay_ms", "Restore delay (ms)",
                  "int", 200, minimum=0, maximum=2000, step=50),
        ]),
        Group("File output (file mode)", [
            Field("output.file_path", "File path", "path", "",
                  placeholder="~/dictations.txt"),
            Field("output.file_mode", "Write mode", "enum", "append", options=[
                ("append", "Append"),
                ("overwrite", "Overwrite"),
            ]),
        ]),
        Group("Output hooks", [
            Field("output.pre_recording_command", "Pre-recording command", "command", "",
                  help="Run before recording starts."),
            Field("output.pre_output_command", "Pre-typing command", "command", "",
                  help="E.g. block modifiers: "
                       "`hyprctl dispatch submap voxtype_suppress`"),
            Field("output.post_output_command", "Post-typing command", "command", "",
                  help="E.g. `hyprctl dispatch submap reset`"),
        ]),
        Group("Post-processing", [
            Field("output.post_process.command", "Post-processing command", "command", "",
                  help="Transcript goes in via stdin; stdout output is typed. "
                       "E.g. LLM cleanup (Ollama), filler word removal."),
            Field("output.post_process.timeout_ms", "Timeout (ms)", "int", 30000,
                  minimum=100, maximum=120000, step=1000),
            Field("output.post_process.trim", "Trim whitespace", "bool", True),
            Field("output.post_process.fallback_on_empty", "Fallback on empty output", "bool", True,
                  help="Uses the original text if the command returns empty."),
        ]),
    ]),

    # ---- NOTIFICATIONS ---------------------------------------------------
    Page("Notifications", "preferences-system-notifications-symbolic", [
        Group("Desktop notifications", [
            Field("output.notification.on_recording_start", "On recording start",
                  "bool", False),
            Field("output.notification.on_recording_stop", "On recording stop",
                  "bool", False),
            Field("output.notification.on_transcription", "On transcription complete",
                  "bool", False, help="Shows the transcribed text."),
            Field("output.notification.show_engine_icon", "Show engine icon",
                  "bool", False),
        ]),
    ]),

    # ---- TEXT ------------------------------------------------------------
    Page("Text", "format-text-rich-symbolic", [
        Group("Text processing", [
            Field("text.spoken_punctuation", "Spoken punctuation", "bool", False,
                  help="Saying 'point' inserts '.', etc."),
            Field("text.smart_auto_submit", "Smart auto-submit", "bool", False,
                  help="Saying 'submit' at the end of a dictation presses Enter "
                       "(the word is removed from the text)."),
            Field("text.filter_filler_words", "Filter filler words", "bool", True,
                  help="Removes 'uh', 'um', etc."),
            Field("text.filler_words", "Filler words", "list",
                  ["uh", "um", "er", "ah", "eh", "hmm", "hm", "mm", "mhm"],
                  help="Comma-separated list.",
                  placeholder="uh, um, er"),
        ]),
        Group("Replacements", [
            # Special field: dedicated key→value editor (handled by a custom widget).
            Field("text.replacements", "Word replacements", "replacements", {},
                  help="Automatic case-insensitive replacements. "
                       "E.g. 'vox type' → 'voxtype'."),
        ]),
    ]),

    # ---- VAD -------------------------------------------------------------
    Page("Voice Detection", "audio-volume-high-symbolic", [
        Group("Voice Activity Detection", [
            Field("vad.enabled", "Enable VAD", "bool", False,
                  help="Filters out silent recordings (avoids Whisper "
                       "hallucinations)."),
            Field("vad.backend", "Backend", "enum", "auto", options=[
                ("auto", "auto"), ("energy", "energy"), ("whisper", "whisper"),
            ]),
            Field("vad.threshold", "Detection threshold", "float", 0.5,
                  minimum=0.0, maximum=1.0, step=0.05,
                  help="0.0 = sensitive, 1.0 = aggressive."),
            Field("vad.min_speech_duration_ms", "Min speech duration (ms)", "int", 100,
                  minimum=0, maximum=5000, step=50),
        ]),
    ]),

    # ---- DISPLAY (OSD + status) ------------------------------------------
    Page("Display", "video-display-symbolic", [
        Group("On-Screen Display (OSD)", [
            Field("osd.enabled", "Enable OSD", "bool", False,
                  help="On-screen display of status and waveform."),
            Field("osd.frontend", "Frontend", "enum", "gtk4", options=[
                ("gtk4", "GTK4"), ("quickshell", "Quickshell"), ("native", "Native"),
            ]),
            Field("osd.position", "Position", "enum", "bottom-center", options=OSD_POSITIONS),
            Field("osd.width_px", "Width (px)", "int", 400, minimum=100, maximum=2000, step=10),
            Field("osd.height_px", "Height (px)", "int", 48, minimum=20, maximum=400, step=4),
            Field("osd.margin_px", "Margin (px)", "int", 24, minimum=0, maximum=400, step=4),
            Field("osd.opacity", "Opacity", "float", 1.0, minimum=0.0, maximum=1.0, step=0.05),
            Field("osd.waveform_gain", "Waveform gain", "float", 10.0,
                  minimum=0.0, maximum=100.0, step=1.0),
        ]),
        Group("Status icon (Waybar/tray)", [
            Field("status.icon_theme", "Icon theme", "enum", "emoji", options=ICON_THEMES),
            Field("status.urgency", "Notification urgency", "enum", "normal", options=[
                ("low", "low (no banner on GNOME)"),
                ("normal", "normal"),
                ("critical", "critical"),
            ]),
        ]),
    ]),

    # ---- MEETING ---------------------------------------------------------
    Page("Meeting", "system-users-symbolic", [
        Group("Meeting mode", [
            Field("meeting.enabled", "Enable meeting mode", "bool", False),
        ]),
        Group("Meeting audio", [
            Field("meeting.audio.source", "Audio source", "enum", "mic", options=[
                ("mic", "Microphone only"),
                ("loopback", "System output (loopback)"),
                ("both", "Both"),
            ]),
        ]),
        Group("Diarization (who speaks)", [
            Field("meeting.diarization.enabled", "Enable diarization", "bool", False,
                  help="Identifies the different speakers."),
        ]),
    ]),

    # ---- PROFILES --------------------------------------------------------
    Page("Profiles", "avatar-default-symbolic", [
        Group("Dictation profiles", [
            # Special field: editor for [profiles.<name>] tables (dedicated widget).
            Field("profiles", "Profiles", "profiles", {},
                  help="Named post-processing profiles. Unset options inherit "
                       "from the main configuration."),
        ], description="Used via 'voxtype record start --profile &lt;name&gt;' or "
                       "via an associated modifier below."),
        Group("Modifier → profile", [
            Field("hotkey.profile_modifiers", "Modifier → profile mappings",
                  "replacements", {},
                  help="Hold this modifier with the dictation key to activate "
                       "the profile. Key: a modifier (LEFTSHIFT, RIGHTCTRL, "
                       "LEFTALT…), value: the profile name. Requires built-in "
                       "hotkey detection."),
        ]),
    ]),
]


def all_fields() -> list[Field]:
    return [f for page in SCHEMA for g in page.groups for f in g.fields]
