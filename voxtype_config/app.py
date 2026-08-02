"""GTK4 / libadwaita application for configuring VoxType."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from . import system  # noqa: E402
from .config_io import ConfigDocument, default_config_path  # noqa: E402
from .schema import SCHEMA, Field  # noqa: E402
from .widgets import FieldRow  # noqa: E402

APP_ID = "earth.tyler.VoxTypeConfig"


def _values_equal(a, b) -> bool:
    """Lenient equality between a widget value and a TOML value."""
    if isinstance(a, list) and isinstance(b, list):
        return [str(x) for x in a] == [str(x) for x in b]
    if isinstance(a, dict) and isinstance(b, dict):
        # order-sensitive: lets us rewrite sorted replacements;
        # recursive for nested values (profiles = dict of dicts)
        if [str(k) for k in a.keys()] != [str(k) for k in b.keys()]:
            return False
        return all(_values_equal(va, vb)
                   for va, vb in zip(a.values(), b.values()))
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return float(a) == float(b)
    return str(a) == str(b)


class Window(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application, config_path=None):
        super().__init__(application=app)
        self.set_default_size(960, 720)
        self.set_title("VoxType Configuration")

        self.config_path = config_path or default_config_path()
        self.doc = ConfigDocument.load(self.config_path)
        self.rows: dict[str, FieldRow] = {}
        self._dirty = False

        self.toasts = Adw.ToastOverlay()
        self.set_content(self.toasts)

        split = Adw.OverlaySplitView(min_sidebar_width=220, max_sidebar_width=280)
        self.split = split

        # ---- main content: header + page stack ----
        self.stack = Adw.ViewStack()
        content_toolbar = Adw.ToolbarView()
        content_toolbar.add_top_bar(self._build_header())
        content_toolbar.set_content(self.stack)
        split.set_content(content_toolbar)

        # ---- sidebar ----
        split.set_sidebar(self._build_sidebar())

        self.toasts.set_child(split)

        self._build_pages()
        self._load_into_rows()
        self._update_subtitle()

    # ------------------------------------------------------------------ UI

    def _build_header(self) -> Adw.HeaderBar:
        header = Adw.HeaderBar()
        self.title_widget = Adw.WindowTitle(title="VoxType Configuration",
                                            subtitle=str(self.config_path))
        header.set_title_widget(self.title_widget)

        save_btn = Gtk.Button(label="Save", css_classes=["suggested-action"])
        save_btn.connect("clicked", lambda *_: self.on_save())
        header.pack_start(save_btn)

        menu = Gio.Menu()
        menu.append("Reload from disk", "win.reload")
        menu.append("Restart VoxType daemon", "win.restart")
        menu.append("Preview TOML file", "win.preview")
        menu.append("About", "win.about")
        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        header.pack_end(menu_btn)

        restart_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        restart_btn.set_tooltip_text("Save and restart daemon")
        restart_btn.connect("clicked", lambda *_: self.on_save_and_restart())
        header.pack_end(restart_btn)

        self._install_actions()
        return header

    def _install_actions(self):
        for name, cb in [
            ("reload", self.on_reload),
            ("restart", self.on_restart_only),
            ("preview", self.on_preview),
            ("about", self.on_about),
        ]:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda a, p, cb=cb: cb())
            self.add_action(action)

    def _build_sidebar(self) -> Adw.ToolbarView:
        tv = Adw.ToolbarView()
        tv.add_top_bar(Adw.HeaderBar(show_title=False))

        self.sidebar_list = Gtk.ListBox(css_classes=["navigation-sidebar"])
        self.sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.sidebar_list.connect("row-selected", self._on_sidebar_selected)

        for page in SCHEMA:
            row = Adw.ActionRow(title=page.title)
            row.add_prefix(Gtk.Image.new_from_icon_name(page.icon))
            row._page_title = page.title  # marker for the ViewStack
            self.sidebar_list.append(row)

        scroller = Gtk.ScrolledWindow(child=self.sidebar_list, vexpand=True)
        tv.set_content(scroller)
        return tv

    def _on_sidebar_selected(self, _list, row):
        if row is not None:
            self.stack.set_visible_child_name(row._page_title)

    def _build_pages(self):
        for page in SCHEMA:
            # Box of groups, wrapped in a wide Clamp that grows with the
            # window (up to 1100 px) — prevents list truncation.
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24,
                          margin_top=24, margin_bottom=24,
                          margin_start=12, margin_end=12)
            for group in page.groups:
                pref_group = Adw.PreferencesGroup(title=group.title,
                                                  description=group.description)
                for fld in group.fields:
                    frow = FieldRow(fld, on_change=self._mark_dirty)
                    self.rows[fld.path] = frow
                    pref_group.add(frow.row)
                box.append(pref_group)
            clamp = Adw.Clamp(maximum_size=1100, tightening_threshold=700, child=box)
            scroller = Gtk.ScrolledWindow(
                child=clamp, vexpand=True,
                hscrollbar_policy=Gtk.PolicyType.NEVER,
            )
            self.stack.add_titled(scroller, page.title, page.title)

        self._wire_xkb_dependency()

        # selects the first page
        first = self.sidebar_list.get_row_at_index(0)
        if first:
            self.sidebar_list.select_row(first)

    def _wire_xkb_dependency(self):
        """The variant list follows the chosen keyboard layout."""
        from . import xkb
        layout_row = self.rows.get("output.dotool_xkb_layout")
        variant_row = self.rows.get("output.dotool_xkb_variant")
        if not layout_row or not variant_row:
            return

        def on_layout_changed(*_):
            layout = layout_row.get_value()
            variant_row.set_enum_options(xkb.variant_options(layout))

        layout_row.row.connect("notify::selected", on_layout_changed)

    # -------------------------------------------------------------- data

    def _load_into_rows(self):
        for path, frow in self.rows.items():
            stored = self.doc.get(path, None)
            frow.set_value(stored)
        self._dirty = False

    def _collect_changes(self) -> int:
        """Writes widget values into the tomlkit document.

        Rules:
        - an EMPTY value ("", [], {}) is never written; the key is removed if
          it was present. (An empty string on a key field crashes VoxType —
          this is also what prevents reintroducing that bug.)
        - otherwise, the key is written if it already exists OR if its value
          differs from the default (to avoid bloating the file with
          unnecessary defaults).
        """
        count = 0
        for path, frow in self.rows.items():
            fld = frow.field
            value = frow.get_value()
            exists = self.doc.has(path)
            is_empty = value == "" or value == [] or value == {}

            if is_empty:
                if exists:
                    self.doc.unset(path)
                    count += 1
                continue

            if exists:
                if not _values_equal(value, self.doc.get(path)):
                    self._write_value(path, fld, value)
                    count += 1
            elif not _values_equal(value, fld.default):
                self._write_value(path, fld, value)
                count += 1
        return count

    def _write_value(self, path: str, fld: Field, value):
        import tomlkit
        if fld.kind in ("list", "driver_order", "multiselect"):
            arr = tomlkit.array()
            arr.extend(value)
            arr.multiline(len(value) > 4)
            self.doc.set(path, arr)
        elif fld.kind == "replacements":
            tbl = tomlkit.inline_table()
            for k, v in value.items():
                tbl[k] = v
            self.doc.set(path, tbl)
        elif fld.kind == "profiles":
            tbl = tomlkit.table(is_super_table=True)
            for name, params in value.items():
                sub = tomlkit.table()
                for k, v in params.items():
                    sub[k] = v
                tbl[name] = sub
            self.doc.set(path, tbl)
        else:
            self.doc.set(path, value)

    # -------------------------------------------------------------- actions

    def _mark_dirty(self):
        self._dirty = True
        self._update_subtitle()

    def _update_subtitle(self):
        status = "● daemon running" if system.daemon_is_active() else "○ daemon stopped"
        dirty = " — unsaved changes" if self._dirty else ""
        self.title_widget.set_subtitle(f"{self.config_path}   ·   {status}{dirty}")

    def _toast(self, text: str, button: str | None = None, action=None):
        t = Adw.Toast(title=text, timeout=4)
        if button and action:
            t.set_button_label(button)
            t.set_action_name("win._toast_action")
            self._toast_cb = action
            if not self.lookup_action("_toast_action"):
                act = Gio.SimpleAction.new("_toast_action", None)
                act.connect("activate", lambda *_: self._toast_cb())
                self.add_action(act)
        self.toasts.add_toast(t)

    def _check_streaming_model(self) -> str | None:
        """Parakeet streaming without tokenizer.model: the daemon won't start.

        We block saving rather than let a config be written that breaks
        VoxType on the next (re)start.
        """
        import os
        streaming = self.rows.get("parakeet.streaming")
        engine = self.rows.get("engine")
        if not streaming or not streaming.get_value():
            return None
        if engine and engine.get_value() != "parakeet":
            return None                      # [parakeet] section inactive
        model_row = self.rows.get("parakeet.model")
        model = str(model_row.get_value() or "") if model_row else ""
        model_dir = model if os.path.isabs(model) else os.path.expanduser(
            f"~/.local/share/voxtype/models/{model}")
        if os.path.isfile(os.path.join(model_dir, "tokenizer.model")):
            return None
        return (f"The model '{model}' has no tokenizer.model file: with "
                "Streaming enabled, the VoxType daemon would refuse to "
                "start.\n\n"
                "First download a streaming-compatible model "
                "(parakeet-unified-en-0.6b, English only) via "
                "'voxtype setup model', or disable streaming.")

    def on_save(self) -> bool:
        problem = self._check_streaming_model()
        if problem:
            self._error_dialog("Parakeet streaming unavailable", problem)
            return False
        try:
            changed = self._collect_changes()
            bak = self.doc.save(make_backup=True)
            self._dirty = False
            self._update_subtitle()
            msg = (f"Saved ({changed} setting(s) modified)."
                   if changed else "No changes to save.")
            if bak and changed:
                msg += " .bak backup created."
            self._toast(msg, button="Restart daemon",
                        action=self._do_restart)
            return True
        except Exception as e:  # noqa: BLE001
            self._error_dialog("Save failed", str(e))
            return False

    def on_save_and_restart(self):
        if self.on_save():
            self._do_restart()

    def _do_restart(self):
        ok, msg = system.restart_daemon()
        GLib.timeout_add(800, self._update_subtitle_once)
        self._toast(msg)

    def _update_subtitle_once(self):
        self._update_subtitle()
        return False

    def on_restart_only(self):
        self._do_restart()

    def on_reload(self):
        self.doc = ConfigDocument.load(self.config_path)
        self._load_into_rows()
        self._update_subtitle()
        self._toast("Configuration reloaded from disk.")

    def on_preview(self):
        # applies in-memory changes (without saving) for the preview
        snapshot = ConfigDocument.load(self.config_path)
        saved_doc = self.doc
        try:
            text = self._preview_text()
        finally:
            self.doc = saved_doc
        del snapshot

        dialog = Adw.Window(transient_for=self, modal=True,
                            default_width=700, default_height=600,
                            title="config.toml Preview")
        tv = Adw.ToolbarView()
        tv.add_top_bar(Adw.HeaderBar())
        textview = Gtk.TextView(editable=False, monospace=True,
                                left_margin=12, right_margin=12,
                                top_margin=12, bottom_margin=12)
        textview.get_buffer().set_text(text)
        tv.set_content(Gtk.ScrolledWindow(child=textview, vexpand=True))
        dialog.set_content(tv)
        dialog.present()

    def _preview_text(self) -> str:
        import copy
        backup = copy.deepcopy(self.doc.doc)
        try:
            self._collect_changes()
            return self.doc.dumps()
        finally:
            self.doc.doc = backup

    def on_about(self):
        about = Adw.AboutWindow(
            transient_for=self,
            application_name="VoxType Configuration",
            application_icon=APP_ID,
            developer_name="VoxType Config",
            version="0.2.3",
            comments="Graphical editor for the VoxType configuration file.\n"
                     "Preserves comments and ordering in config.toml.",
            website="https://github.com/",
        )
        about.present()

    def _error_dialog(self, title: str, detail: str):
        dlg = Adw.MessageDialog(transient_for=self, heading=title, body=detail)
        dlg.add_response("ok", "OK")
        dlg.present()


class Application(Adw.Application):
    def __init__(self, config_path=None):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self._config_path = config_path
        self.win = None

    def do_activate(self):
        if not self.win:
            self.win = Window(self, self._config_path)
        self.win.present()

    def do_open(self, files, n_files, hint):
        if files:
            self._config_path = files[0].get_path()
        self.do_activate()


def main(argv=None):
    import sys
    app = Application()
    return app.run(argv if argv is not None else sys.argv)
