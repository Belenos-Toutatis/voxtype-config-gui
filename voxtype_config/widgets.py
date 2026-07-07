"""Construction des lignes libadwaita à partir des Field du schéma.

Chaque FieldRow encapsule un widget Adw et expose get_value()/set_value()
dans le type Python attendu par le TOML.
"""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk, GObject, Pango  # noqa: E402

from .schema import Field  # noqa: E402
from . import keys as keymap  # noqa: E402


def _split_list(text: str) -> list[str]:
    return [p.strip() for p in text.split(",") if p.strip()]


def _wrap_factory() -> Gtk.SignalListItemFactory:
    """Factory de ComboRow : libellés qui s'enroulent au lieu d'être tronqués (…)."""
    factory = Gtk.SignalListItemFactory()

    def on_setup(_f, item):
        label = Gtk.Label(xalign=0, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR)
        item.set_child(label)

    def on_bind(_f, item):
        obj = item.get_item()
        if obj is not None:
            item.get_child().set_label(obj.get_string())

    factory.connect("setup", on_setup)
    factory.connect("bind", on_bind)
    return factory


class FieldRow(GObject.Object):
    """Une ligne de préférence reliée à un Field. Émet 'changed' à toute édition."""

    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self, field: Field, on_change=None):
        super().__init__()
        self.field = field
        self.row: Gtk.Widget
        self._enum_values: list[str] = []
        self._build()
        if on_change:
            self.connect("changed", lambda *_: on_change())

    # -- construction ------------------------------------------------------

    def _emit_changed(self, *_):
        self.emit("changed")

    def _subtitle(self) -> str:
        return self.field.help

    def _build(self):
        f = self.field
        kind = f.kind

        if kind == "bool":
            row = Adw.SwitchRow(title=f.label, subtitle=self._subtitle())
            row.connect("notify::active", self._emit_changed)
            self.row = row

        elif kind == "enum":
            opts = f.dynamic_options() if f.dynamic_options else f.options
            self._enum_values = [v for v, _ in opts]
            model = Gtk.StringList()
            for _, lbl in opts:
                model.append(lbl)
            row = Adw.ComboRow(title=f.label, subtitle=self._subtitle(), model=model)
            row.set_factory(_wrap_factory())          # pas de troncature « … »
            row.connect("notify::selected", self._emit_changed)
            self.row = row

        elif kind in ("int", "float"):
            digits = 0 if kind == "int" else 2
            adj = Gtk.Adjustment(
                lower=f.minimum, upper=f.maximum, step_increment=f.step,
                page_increment=f.step * 10,
            )
            row = Adw.SpinRow(title=f.label, subtitle=self._subtitle(),
                              adjustment=adj, digits=digits)
            row.connect("notify::value", self._emit_changed)
            self.row = row

        elif kind in ("string", "path", "command", "list"):
            row = Adw.EntryRow(title=f.label)
            if f.placeholder:
                row.set_text("")
            # sous-titre non supporté par EntryRow → on ajoute une info-bulle
            if self._subtitle():
                row.set_tooltip_text(self._subtitle())
            row.connect("changed", self._emit_changed)
            if kind == "path":
                btn = Gtk.Button(icon_name="document-open-symbolic",
                                 valign=Gtk.Align.CENTER, css_classes=["flat"])
                btn.connect("clicked", self._on_pick_file)
                row.add_suffix(btn)
            self.row = row
            self._entry = row

        elif kind == "key":
            self.row = KeyRow(f, self._emit_changed)

        elif kind == "driver_order":
            self.row = DriverOrderRow(f, self._emit_changed)

        elif kind == "multiselect":
            self.row = MultiSelectRow(f, self._emit_changed)

        elif kind == "replacements":
            self.row = ReplacementsRow(f, self._emit_changed)

        elif kind == "profiles":
            self.row = ProfilesRow(f, self._emit_changed)

        else:
            raise ValueError(f"type de champ inconnu : {kind}")

    def _on_pick_file(self, _btn):
        dialog = Gtk.FileDialog(title=self.field.label)
        win = self.row.get_root()

        def done(dlg, res):
            try:
                file = dlg.open_finish(res)
                if file:
                    self._entry.set_text(file.get_path() or "")
            except Exception:
                pass

        dialog.open(win, None, done)

    # -- valeurs -----------------------------------------------------------

    def get_value(self):
        f = self.field
        kind = f.kind
        if kind == "bool":
            return self.row.get_active()
        if kind == "enum":
            idx = self.row.get_selected()
            if 0 <= idx < len(self._enum_values):
                return self._enum_values[idx]
            return f.default
        if kind == "int":
            return int(self.row.get_value())
        if kind == "float":
            return round(float(self.row.get_value()), 4)
        if kind == "list":
            return _split_list(self._entry.get_text())
        if kind in ("string", "path", "command"):
            return self._entry.get_text()
        if kind in ("replacements", "profiles", "key", "driver_order", "multiselect"):
            return self.row.get_value()
        return None

    def set_enum_options(self, opts: list[tuple[str, str]]):
        """Repeuple une liste déroulante (réactivité, ex. variantes selon disposition)."""
        if self.field.kind != "enum":
            return
        current = self.get_value()
        self._enum_values = [v for v, _ in opts]
        model = Gtk.StringList()
        for _, lbl in opts:
            model.append(lbl)
        self.row.set_model(model)
        self.row.set_factory(_wrap_factory())
        if current in self._enum_values:
            self.row.set_selected(self._enum_values.index(current))
        else:
            self.row.set_selected(0)

    def set_value(self, value):
        f = self.field
        kind = f.kind
        if value is None:
            value = f.default
        if kind == "bool":
            self.row.set_active(bool(value))
        elif kind == "enum":
            val = str(value)
            if val in self._enum_values:
                self.row.set_selected(self._enum_values.index(val))
            else:
                # valeur hors-liste : on l'ajoute pour ne pas la perdre
                model = self.row.get_model()
                model.append(f"{val} (actuel)")
                self._enum_values.append(val)
                self.row.set_selected(len(self._enum_values) - 1)
        elif kind in ("int", "float"):
            try:
                self.row.set_value(float(value))
            except (TypeError, ValueError):
                self.row.set_value(float(f.default or 0))
        elif kind == "list":
            items = value if isinstance(value, list) else _split_list(str(value))
            self._entry.set_text(", ".join(str(x) for x in items))
        elif kind in ("string", "path", "command"):
            self._entry.set_text("" if value is None else str(value))
        elif kind in ("replacements", "profiles", "key", "driver_order", "multiselect"):
            self.row.set_value(value)


class KeyRow(Adw.EntryRow):
    """Champ de touche : saisie libre + capture en direct + suggestions."""

    def __init__(self, field: Field, on_change):
        super().__init__(title=field.label)
        self.field = field
        self._on_change = on_change
        self._base_tooltip = field.help or ""
        if self._base_tooltip:
            self.set_tooltip_text(self._base_tooltip)
        self.connect("changed", self._on_changed)

        # bouton « capturer »
        capture_btn = Gtk.Button(icon_name="media-record-symbolic",
                                 valign=Gtk.Align.CENTER, css_classes=["flat"])
        capture_btn.set_tooltip_text("Capturer : appuyez sur une touche")
        capture_btn.connect("clicked", self._on_capture)
        self.add_suffix(capture_btn)

        # menu de suggestions de touches courantes
        menu = Gio.Menu()
        for name in keymap.COMMON_KEYS:
            menu.append(name, f"keyrow.set::{name}")
        self._action_group = Gio.SimpleActionGroup()
        act = Gio.SimpleAction.new("set", GLib.VariantType.new("s"))
        act.connect("activate", lambda a, p: self.set_text(p.get_string()))
        self._action_group.add_action(act)
        self.insert_action_group("keyrow", self._action_group)
        menu_btn = Gtk.MenuButton(icon_name="pan-down-symbolic",
                                  valign=Gtk.Align.CENTER, css_classes=["flat"],
                                  menu_model=menu)
        menu_btn.set_tooltip_text("Touches courantes")
        self.add_suffix(menu_btn)

    def _on_changed(self, *_):
        self._validate()
        self._on_change()

    def _validate(self):
        """Marque le champ en rouge si la touche n'est pas reconnue par VoxType."""
        text = self.get_text().strip()
        if keymap.is_valid_key(text):
            self.remove_css_class("error")
            self.set_tooltip_text(self._base_tooltip)
        else:
            self.add_css_class("error")
            self.set_tooltip_text(
                f"« {text} » n'est pas un nom de touche reconnu par VoxType.\n"
                "Utilisez « Capturer », une suggestion, ou un keycode préfixé "
                "(EVTEST_226, WEV_234)."
            )

    def _on_capture(self, _btn):
        win = Adw.Window(transient_for=self.get_root(), modal=True,
                         default_width=360, default_height=180,
                         title="Capture de touche")
        tv = Adw.ToolbarView()
        tv.add_top_bar(Adw.HeaderBar(show_title=False))
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER,
                      margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        box.append(Gtk.Image.new_from_icon_name("input-keyboard-symbolic"))
        box.append(Gtk.Label(label="Appuyez sur la touche à utiliser…",
                             css_classes=["title-3"]))
        hint = Gtk.Label(label="(Échap pour annuler la fenêtre via le bouton)",
                         css_classes=["dim-label"])
        box.append(hint)
        cancel = Gtk.Button(label="Annuler", halign=Gtk.Align.CENTER)
        cancel.connect("clicked", lambda *_: win.close())
        box.append(cancel)
        tv.set_content(box)
        win.set_content(tv)

        ctrl = Gtk.EventControllerKey()

        def on_key(_c, keyval, keycode, state):
            name = keymap.evdev_name_from_keycode(keycode)
            if name:
                self.set_text(name)
            win.close()
            return True

        ctrl.connect("key-pressed", on_key)
        win.add_controller(ctrl)
        win.present()

    def get_value(self):
        return self.get_text().strip()

    def set_value(self, value):
        self.set_text("" if value is None else str(value))
        self._validate()


class DriverOrderRow(Adw.ExpanderRow):
    """Ordre des pilotes de frappe : une liste déroulante par position."""

    def __init__(self, field: Field, on_change):
        super().__init__(title=field.label, subtitle=field.help)
        self.field = field
        self._on_change = on_change
        self._options = list(field.options)              # [(val, label), …]
        self._values = [v for v, _ in self._options]
        self._combos: list[Adw.ComboRow] = []

        n_slots = len(self._options)                     # un emplacement par pilote
        for i in range(n_slots):
            model = Gtk.StringList()
            model.append("— aucun —")
            for _, lbl in self._options:
                model.append(lbl)
            combo = Adw.ComboRow(title=f"Position {i + 1}", model=model)
            combo.set_factory(_wrap_factory())
            combo.connect("notify::selected", self._on_combo_changed)
            self._combos.append(combo)
            self.add_row(combo)

    def _on_combo_changed(self, *_):
        self._update_subtitle()
        self._on_change()

    def _update_subtitle(self):
        order = self.get_value()
        self.set_subtitle(" → ".join(order) if order else "aucun pilote sélectionné")

    def get_value(self) -> list[str]:
        order: list[str] = []
        for combo in self._combos:
            idx = combo.get_selected()
            if idx > 0:                                  # 0 = « aucun »
                val = self._values[idx - 1]
                if val not in order:                     # pas de doublon
                    order.append(val)
        return order

    def set_value(self, value):
        items = value if isinstance(value, list) else (value or [])
        items = [str(x) for x in items]
        for i, combo in enumerate(self._combos):
            if i < len(items) and items[i] in self._values:
                combo.set_selected(self._values.index(items[i]) + 1)
            else:
                combo.set_selected(0)
        self._update_subtitle()


class MultiSelectRow(Adw.ExpanderRow):
    """Sélection multiple via interrupteurs (ex. modificateurs de raccourci)."""

    def __init__(self, field: Field, on_change):
        super().__init__(title=field.label, subtitle=field.help)
        self._on_change = on_change
        self._switches: dict[str, Adw.SwitchRow] = {}
        for code, label in field.options:
            sw = Adw.SwitchRow(title=label, subtitle=code)
            sw.connect("notify::active", self._on_toggle)
            self._switches[code] = sw
            self.add_row(sw)

    def _on_toggle(self, *_):
        self._update_subtitle()
        self._on_change()

    def _update_subtitle(self):
        sel = self.get_value()
        self.set_subtitle(", ".join(sel) if sel else "aucun")

    def get_value(self) -> list[str]:
        return [code for code, sw in self._switches.items() if sw.get_active()]

    def set_value(self, value):
        items = set(value or [])
        for code, sw in self._switches.items():
            sw.set_active(code in items)
        self._update_subtitle()


class ReplacementsRow(Gtk.Box):
    """Tableau à deux colonnes (Dit → Remplacé par) pour les remplacements de mots.

    Trié par ordre alphabétique de la colonne « Dit » à l'ouverture, à l'ajout
    et à l'enregistrement.
    """

    def __init__(self, field: Field, on_change):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                         margin_top=6, margin_bottom=6,
                         margin_start=6, margin_end=6)
        self._on_change = on_change
        self._rows: list[dict] = []          # {row, key, value}

        # En-tête de colonnes
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6,
                         margin_start=6, margin_end=6)
        h1 = Gtk.Label(label="Dit (entendu)", xalign=0, hexpand=True,
                       css_classes=["heading", "dim-label"])
        h2 = Gtk.Label(label="Remplacé par", xalign=0, hexpand=True,
                       css_classes=["heading", "dim-label"])
        header.append(h1)
        header.append(h2)
        spacer = Gtk.Box()
        spacer.set_size_request(34, -1)      # aligne avec les boutons « corbeille »
        header.append(spacer)
        self.append(header)

        # Liste des lignes (style « boxed-list » natif)
        self._listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE,
                                    css_classes=["boxed-list"])
        self.append(self._listbox)

        # Barre d'action
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6,
                         margin_top=6)
        add_btn = Gtk.Button(child=Adw.ButtonContent(
            icon_name="list-add-symbolic", label="Ajouter"))
        add_btn.add_css_class("flat")
        add_btn.connect("clicked", self._on_add)
        sort_btn = Gtk.Button(child=Adw.ButtonContent(
            icon_name="view-sort-ascending-symbolic", label="Trier"))
        sort_btn.add_css_class("flat")
        sort_btn.set_tooltip_text("Reclasser par ordre alphabétique")
        sort_btn.connect("clicked", lambda *_: (self._resort(), self._on_change()))
        self._count = Gtk.Label(css_classes=["dim-label"], hexpand=True, xalign=1)
        footer.append(add_btn)
        footer.append(sort_btn)
        footer.append(self._count)
        self.append(footer)

    # -- gestion des lignes -------------------------------------------------

    def _make_row(self, key: str, val: str) -> dict:
        row = Gtk.ListBoxRow(activatable=False)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6,
                       margin_top=4, margin_bottom=4, margin_start=6, margin_end=6)
        key_e = Gtk.Entry(text=key, hexpand=True, placeholder_text="vox type")
        val_e = Gtk.Entry(text=val, hexpand=True, placeholder_text="voxtype")
        trash = Gtk.Button(icon_name="user-trash-symbolic",
                           valign=Gtk.Align.CENTER, css_classes=["flat"])
        entry = {"row": row, "key": key_e, "value": val_e}
        trash.connect("clicked", lambda *_: self._remove(entry))
        key_e.connect("changed", lambda *_: self._on_change())
        val_e.connect("changed", lambda *_: self._on_change())
        hbox.append(key_e)
        hbox.append(val_e)
        hbox.append(trash)
        row.set_child(hbox)
        return entry

    def _append(self, key: str, val: str) -> dict:
        entry = self._make_row(key, val)
        self._listbox.append(entry["row"])
        self._rows.append(entry)
        self._update_count()
        return entry

    def _remove(self, entry: dict):
        self._listbox.remove(entry["row"])
        self._rows.remove(entry)
        self._update_count()
        self._on_change()

    def _clear(self):
        for entry in list(self._rows):
            self._listbox.remove(entry["row"])
        self._rows = []

    def _on_add(self, _btn):
        entry = self._append("", "")
        entry["key"].grab_focus()
        self._on_change()

    def _resort(self):
        items = self.get_value()             # déjà trié
        self.set_value(items)

    def _update_count(self):
        n = len(self._rows)
        self._count.set_label(f"{n} remplacement" + ("s" if n > 1 else ""))

    # -- valeurs ------------------------------------------------------------

    def get_value(self) -> dict:
        pairs = []
        for entry in self._rows:
            k = entry["key"].get_text().strip()
            if k:
                pairs.append((k, entry["value"].get_text()))
        pairs.sort(key=lambda kv: kv[0].casefold())   # tri alphabétique
        return dict(pairs)

    def set_value(self, mapping: dict):
        self._clear()
        items = sorted((mapping or {}).items(), key=lambda kv: str(kv[0]).casefold())
        for k, v in items:
            self._append(str(k), str(v))
        self._update_count()


PROFILE_OUTPUT_MODES = [
    ("", "(hériter du mode principal)"),
    ("type", "Frappe directe"),
    ("paste", "Coller"),
    ("clipboard", "Presse-papiers seul"),
]


class ProfilesRow(Gtk.Box):
    """Éditeur des profils nommés ([profiles.<nom>]).

    Chaque profil surcharge la commande de post-traitement, son timeout et/ou
    le mode de sortie ; le reste hérite de la configuration principale.
    """

    def __init__(self, field: Field, on_change):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                         margin_top=6, margin_bottom=6,
                         margin_start=6, margin_end=6)
        self._on_change = on_change
        self._profiles: list[dict] = []      # {expander, name, cmd, timeout, mode}

        self._listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE,
                                    css_classes=["boxed-list"])
        self.append(self._listbox)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6,
                         margin_top=6)
        add_btn = Gtk.Button(child=Adw.ButtonContent(
            icon_name="list-add-symbolic", label="Ajouter un profil"))
        add_btn.add_css_class("flat")
        add_btn.connect("clicked", self._on_add)
        self._count = Gtk.Label(css_classes=["dim-label"], hexpand=True, xalign=1)
        footer.append(add_btn)
        footer.append(self._count)
        self.append(footer)

    # -- gestion des profils -------------------------------------------------

    def _make_profile(self, name: str, data: dict) -> dict:
        exp = Adw.ExpanderRow(title=name or "(sans nom)")

        name_e = Adw.EntryRow(title="Nom du profil")
        name_e.set_text(name)
        cmd_e = Adw.EntryRow(title="Commande de post-traitement")
        cmd_e.set_text(str(data.get("post_process_command", "") or ""))
        cmd_e.set_tooltip_text("Le transcript passe par stdin, la sortie stdout "
                               "est tapée. Vide = hériter.")

        adj = Gtk.Adjustment(lower=0, upper=120000, step_increment=1000,
                             page_increment=10000)
        timeout = Adw.SpinRow(title="Timeout (ms)", subtitle="0 = hériter",
                              adjustment=adj, digits=0)
        try:
            timeout.set_value(float(data.get("post_process_timeout_ms", 0) or 0))
        except (TypeError, ValueError):
            timeout.set_value(0)

        mode_model = Gtk.StringList()
        for _, lbl in PROFILE_OUTPUT_MODES:
            mode_model.append(lbl)
        mode = Adw.ComboRow(title="Mode de sortie", model=mode_model)
        mode.set_factory(_wrap_factory())
        values = [v for v, _ in PROFILE_OUTPUT_MODES]
        current = str(data.get("output_mode", "") or "")
        mode.set_selected(values.index(current) if current in values else 0)

        trash = Gtk.Button(icon_name="user-trash-symbolic",
                           valign=Gtk.Align.CENTER, css_classes=["flat"])
        trash.set_tooltip_text("Supprimer ce profil")
        exp.add_suffix(trash)

        entry = {"expander": exp, "name": name_e, "cmd": cmd_e,
                 "timeout": timeout, "mode": mode}
        trash.connect("clicked", lambda *_: self._remove(entry))
        name_e.connect("changed", lambda *_: self._on_name_changed(entry))
        cmd_e.connect("changed", lambda *_: self._on_change())
        timeout.connect("notify::value", lambda *_: self._on_change())
        mode.connect("notify::selected", lambda *_: self._on_change())

        for row in (name_e, cmd_e, timeout, mode):
            exp.add_row(row)
        return entry

    def _on_name_changed(self, entry: dict):
        name = entry["name"].get_text().strip()
        entry["expander"].set_title(name or "(sans nom)")
        self._on_change()

    def _append(self, name: str, data: dict) -> dict:
        entry = self._make_profile(name, data)
        self._listbox.append(entry["expander"])
        self._profiles.append(entry)
        self._update_count()
        return entry

    def _remove(self, entry: dict):
        self._listbox.remove(entry["expander"])
        self._profiles.remove(entry)
        self._update_count()
        self._on_change()

    def _clear(self):
        for entry in list(self._profiles):
            self._listbox.remove(entry["expander"])
        self._profiles = []

    def _on_add(self, _btn):
        entry = self._append("", {})
        entry["expander"].set_expanded(True)
        entry["name"].grab_focus()
        self._on_change()

    def _update_count(self):
        n = len(self._profiles)
        self._count.set_label(f"{n} profil" + ("s" if n > 1 else ""))

    # -- valeurs ------------------------------------------------------------

    def get_value(self) -> dict:
        out: dict[str, dict] = {}
        for entry in self._profiles:
            name = entry["name"].get_text().strip()
            if not name:
                continue                     # profil sans nom : ignoré
            params: dict = {}
            cmd = entry["cmd"].get_text().strip()
            if cmd:
                params["post_process_command"] = cmd
            timeout = int(entry["timeout"].get_value())
            if timeout > 0:
                params["post_process_timeout_ms"] = timeout
            idx = entry["mode"].get_selected()
            values = [v for v, _ in PROFILE_OUTPUT_MODES]
            if 0 < idx < len(values):
                params["output_mode"] = values[idx]
            out[name] = params
        return out

    def set_value(self, mapping: dict):
        self._clear()
        items = sorted((mapping or {}).items(), key=lambda kv: str(kv[0]).casefold())
        for name, data in items:
            self._append(str(name), dict(data) if isinstance(data, dict) else {})
        self._update_count()
