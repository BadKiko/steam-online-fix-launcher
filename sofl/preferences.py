# preferences.py
#
# Copyright 2022-2023 badkiko
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later


import logging
import re
from pathlib import Path
from shutil import rmtree
from sys import platform
from typing import Any, Callable, Optional
import os

from gi.repository import Adw, Gio, GLib, Gtk

from sofl import shared
from sofl.errors.friendly_error import FriendlyError
from sofl.game import Game
from sofl.importer.bottles_source import BottlesSource
from sofl.importer.desktop_source import DesktopSource
from sofl.importer.flatpak_source import FlatpakSource
from sofl.importer.heroic_source import HeroicSource
from sofl.importer.itch_source import ItchSource
from sofl.importer.legendary_source import LegendarySource
from sofl.importer.location import UnresolvableLocationError
from sofl.importer.lutris_source import LutrisSource
from sofl.importer.retroarch_source import RetroarchSource
from sofl.importer.source import Source
from sofl.importer.steam_source import SteamSource
from sofl.store.managers.sgdb_manager import SgdbManager
from sofl.utils.create_dialog import create_dialog


@Gtk.Template(resource_path=shared.PREFIX + "/gtk/preferences.ui")
class SOFLPreferences(Adw.PreferencesDialog):
    __gtype_name__ = "SOFLPreferences"

    general_page: Adw.PreferencesPage = Gtk.Template.Child()
    import_page: Adw.PreferencesPage = Gtk.Template.Child()
    sgdb_page: Adw.PreferencesPage = Gtk.Template.Child()

    sources_group: Adw.PreferencesGroup = Gtk.Template.Child()

    exit_after_launch_switch: Adw.SwitchRow = Gtk.Template.Child()
    cover_launches_game_switch: Adw.SwitchRow = Gtk.Template.Child()
    high_quality_images_switch: Adw.SwitchRow = Gtk.Template.Child()
    force_theme_switch: Adw.SwitchRow = Gtk.Template.Child()

    auto_import_switch: Adw.SwitchRow = Gtk.Template.Child()
    remove_missing_switch: Adw.SwitchRow = Gtk.Template.Child()

    steam_expander_row: Adw.ExpanderRow = Gtk.Template.Child()
    steam_data_action_row: Adw.ActionRow = Gtk.Template.Child()
    steam_data_file_chooser_button: Gtk.Button = Gtk.Template.Child()

    lutris_expander_row: Adw.ExpanderRowClass = Gtk.Template.Child()
    lutris_data_action_row: Adw.ActionRow = Gtk.Template.Child()
    lutris_data_file_chooser_button: Gtk.Button = Gtk.Template.Child()
    lutris_import_steam_switch: Adw.SwitchRow = Gtk.Template.Child()
    lutris_import_flatpak_switch: Adw.SwitchRow = Gtk.Template.Child()

    heroic_expander_row: Adw.ExpanderRow = Gtk.Template.Child()
    heroic_config_action_row: Adw.ActionRow = Gtk.Template.Child()
    heroic_config_file_chooser_button: Gtk.Button = Gtk.Template.Child()
    heroic_import_epic_switch: Adw.SwitchRow = Gtk.Template.Child()
    heroic_import_gog_switch: Adw.SwitchRow = Gtk.Template.Child()
    heroic_import_amazon_switch: Adw.SwitchRow = Gtk.Template.Child()
    heroic_import_sideload_switch: Adw.SwitchRow = Gtk.Template.Child()

    bottles_expander_row: Adw.ExpanderRow = Gtk.Template.Child()
    bottles_data_action_row: Adw.ActionRow = Gtk.Template.Child()
    bottles_data_file_chooser_button: Gtk.Button = Gtk.Template.Child()

    itch_expander_row: Adw.ExpanderRow = Gtk.Template.Child()
    itch_config_action_row: Adw.ActionRow = Gtk.Template.Child()
    itch_config_file_chooser_button: Gtk.Button = Gtk.Template.Child()

    legendary_expander_row: Adw.ExpanderRow = Gtk.Template.Child()
    legendary_config_action_row: Adw.ActionRow = Gtk.Template.Child()
    legendary_config_file_chooser_button: Gtk.Button = Gtk.Template.Child()

    retroarch_expander_row: Adw.ExpanderRow = Gtk.Template.Child()
    retroarch_config_action_row: Adw.ActionRow = Gtk.Template.Child()
    retroarch_config_file_chooser_button: Gtk.Button = Gtk.Template.Child()

    flatpak_expander_row: Adw.ExpanderRow = Gtk.Template.Child()
    flatpak_system_data_action_row: Adw.ActionRow = Gtk.Template.Child()
    flatpak_system_data_file_chooser_button: Gtk.Button = Gtk.Template.Child()
    flatpak_user_data_action_row: Adw.ActionRow = Gtk.Template.Child()
    flatpak_user_data_file_chooser_button: Gtk.Button = Gtk.Template.Child()
    flatpak_import_launchers_switch: Adw.SwitchRow = Gtk.Template.Child()

    desktop_switch: Adw.SwitchRow = Gtk.Template.Child()

    sgdb_key_group: Adw.PreferencesGroup = Gtk.Template.Child()
    sgdb_key_entry_row: Adw.EntryRow = Gtk.Template.Child()
    sgdb_switch: Adw.SwitchRow = Gtk.Template.Child()
    sgdb_prefer_switch: Adw.SwitchRow = Gtk.Template.Child()
    sgdb_animated_switch: Adw.SwitchRow = Gtk.Template.Child()
    sgdb_fetch_button: Gtk.Button = Gtk.Template.Child()
    sgdb_stack: Gtk.Stack = Gtk.Template.Child()
    sgdb_spinner: Gtk.Spinner = Gtk.Template.Child()

    danger_zone_group = Gtk.Template.Child()
    remove_all_games_button_row = Gtk.Template.Child()
    reset_button_row = Gtk.Template.Child()

    # Online-Fix
    online_fix_entry_row: Adw.EntryRow = Gtk.Template.Child()
    online_fix_file_chooser_button: Gtk.Button = Gtk.Template.Child()
    online_fix_launcher_combo: Adw.ComboRow = Gtk.Template.Child()
    online_fix_auto_patch_switch: Adw.SwitchRow = Gtk.Template.Child()
    online_fix_dll_override_entry: Adw.EntryRow = Gtk.Template.Child()
    online_fix_dll_group: Adw.PreferencesGroup = Gtk.Template.Child()
    online_fix_patches_group: Adw.PreferencesGroup = Gtk.Template.Child()
    online_fix_steam_appid_switch: Adw.SwitchRow = Gtk.Template.Child()
    online_fix_patch_steam_fix_64: Adw.SwitchRow = Gtk.Template.Child()
    online_fix_proton_combo: Adw.ComboRow = Gtk.Template.Child()
    online_fix_umu_proton_combo: Adw.ComboRow = Gtk.Template.Child()
    online_fix_umu_banner_box: Gtk.Box = Gtk.Template.Child()
    online_fix_umu_info_button: Gtk.Button = Gtk.Template.Child()

    removed_games: set[Game] = set()
    warning_menu_buttons: dict = {}

    is_open = False

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        # Make it so only one dialog can be open at a time
        self.__class__.is_open = True
        self.connect("closed", lambda *_: self.set_is_open(False))

        self.file_chooser = Gtk.FileDialog()

        self.toast = Adw.Toast.new(_("All games removed"))
        self.toast.set_button_label(_("Undo"))
        self.toast.connect("button-clicked", self.undo_remove_all, None)
        self.toast.set_priority(Adw.ToastPriority.HIGH)

        (shortcut_controller := Gtk.ShortcutController()).add_shortcut(
            Gtk.Shortcut.new(
                Gtk.ShortcutTrigger.parse_string("<primary>z"),
                Gtk.CallbackAction.new(self.undo_remove_all),
            )
        )
        self.add_controller(shortcut_controller)

        # General
        self.remove_all_games_button_row.connect("activated", self.remove_all_games)

        # Debug
        if shared.PROFILE == "development":
            self.reset_button_row.set_visible(True)
            self.reset_button_row.connect("activated", self.reset_app)

        # Sources settings
        for source_class in (
            BottlesSource,
            FlatpakSource,
            HeroicSource,
            ItchSource,
            LegendarySource,
            LutrisSource,
            RetroarchSource,
            SteamSource,
        ):
            source = source_class()
            if not source.is_available:
                expander_row = getattr(self, f"{source.source_id}_expander_row")
                expander_row.set_visible(False)
            else:
                self.init_source_row(source)

        # Special case for the desktop source
        if not DesktopSource().is_available:
            self.desktop_switch.set_visible(False)

        # SteamGridDB
        def sgdb_key_changed(*_args: Any) -> None:
            shared.schema.set_string("sgdb-key", self.sgdb_key_entry_row.get_text())

        self.sgdb_key_entry_row.set_text(shared.schema.get_string("sgdb-key"))
        self.sgdb_key_entry_row.connect("changed", sgdb_key_changed)

        self.sgdb_key_group.set_description(
            _(
                "An API key is required to use SteamGridDB. You can generate one {}here{}."
            ).format(
                '<a href="https://www.steamgriddb.com/profile/preferences/api">', "</a>"
            )
        )

        # Online-Fix setup
        self.setup_online_fix_settings()
        # Connect UMU info button to show description
        try:

            def show_umu_info(_widget: Any, *_args: Any) -> None:
                title = _("About UMU Launcher")
                body = _(
                    "UMU Launcher is a launcher similar to Steam API, and it may work if the game does not function with Steam API. "
                    "For installation, please visit https://github.com/Open-Wine-Components/umu-launcher."
                )
                create_dialog(self, title, body)

            self.online_fix_umu_info_button.connect("clicked", show_umu_info)
        except Exception:
            pass

        def update_sgdb(*_args: Any) -> None:
            counter = 0
            games_len = len(shared.store)
            sgdb_manager = shared.store.managers[SgdbManager]
            sgdb_manager.reset_cancellable()

            self.sgdb_spinner.set_visible(True)
            self.sgdb_stack.set_visible_child(self.sgdb_spinner)

            self.add_toast(download_toast := Adw.Toast.new(_("Downloading covers…")))

            def update_cover_callback(manager: SgdbManager) -> None:
                nonlocal counter
                nonlocal games_len
                nonlocal download_toast

                counter += 1
                if counter != games_len:
                    return

                for error in manager.collect_errors():
                    if isinstance(error, FriendlyError):
                        create_dialog(self, error.title, error.subtitle)
                        break

                for game in shared.store:
                    game.update()

                toast = Adw.Toast.new(_("Covers updated"))
                toast.set_priority(Adw.ToastPriority.HIGH)
                download_toast.dismiss()
                self.add_toast(toast)

                self.sgdb_spinner.set_visible(False)
                self.sgdb_stack.set_visible_child(self.sgdb_fetch_button)

            for game in shared.store:
                sgdb_manager.process_game(game, {}, update_cover_callback)

        self.sgdb_fetch_button.connect("clicked", update_sgdb)

        # Switches
        self.bind_switches(
            {
                "exit-after-launch",
                "cover-launches-game",
                "high-quality-images",
                "auto-import",
                "remove-missing",
                "lutris-import-steam",
                "lutris-import-flatpak",
                "heroic-import-epic",
                "heroic-import-gog",
                "heroic-import-amazon",
                "heroic-import-sideload",
                "flatpak-import-launchers",
                "sgdb",
                "sgdb-prefer",
                "sgdb-animated",
                "desktop",
            }
        )

        # Синхронизация переключателя темы с настройкой force-theme
        theme = shared.schema.get_string("force-theme")
        self.force_theme_switch.set_active(theme == "dark")

        def on_theme_switch(row, _param):
            shared.schema.set_string(
                "force-theme", "dark" if row.get_active() else "light"
            )
            # (опционально) сразу применить тему:
            from gi.repository import Adw

            style_manager = Adw.StyleManager.get_default()
            style_manager.set_color_scheme(
                Adw.ColorScheme.FORCE_DARK
                if row.get_active()
                else Adw.ColorScheme.FORCE_LIGHT
            )

        self.force_theme_switch.connect("notify::active", on_theme_switch)

        def set_sgdb_sensitive(widget: Adw.EntryRow) -> None:
            if not widget.get_text():
                shared.schema.set_boolean("sgdb", False)

            self.sgdb_switch.set_sensitive(widget.get_text())

        self.sgdb_key_entry_row.connect("changed", set_sgdb_sensitive)
        set_sgdb_sensitive(self.sgdb_key_entry_row)

    def set_is_open(self, is_open: bool) -> None:
        self.__class__.is_open = is_open

    def get_switch(self, setting: str) -> Any:
        return getattr(self, f'{setting.replace("-", "_")}_switch')

    def bind_switches(self, settings: set[str]) -> None:
        for setting in settings:
            shared.schema.bind(
                setting,
                self.get_switch(setting),
                "active",
                Gio.SettingsBindFlags.DEFAULT,
            )

    def choose_folder(
        self, _widget: Any, callback: Callable, callback_data: Optional[str] = None
    ) -> None:
        self.file_chooser.select_folder(shared.win, None, callback, callback_data)

    def undo_remove_all(self, *_args: Any) -> bool:
        shared.win.get_application().state = shared.AppState.UNDO_REMOVE_ALL_GAMES
        for game in self.removed_games:
            game.removed = False
            game.save()
            game.update()

        self.removed_games = set()
        self.toast.dismiss()
        shared.win.get_application().state = shared.AppState.DEFAULT
        shared.win.create_source_rows()

        return True

    def remove_all_games(self, *_args: Any) -> None:
        shared.win.get_application().state = shared.AppState.REMOVE_ALL_GAMES
        shared.win.row_selected(None, shared.win.all_games_row_box.get_parent())
        for game in shared.store:
            if not game.removed:
                self.removed_games.add(game)
                game.removed = True
                game.save()
                game.update()

        if shared.win.navigation_view.get_visible_page() == shared.win.details_page:
            shared.win.navigation_view.pop()

        self.add_toast(self.toast)
        shared.win.get_application().state = shared.AppState.DEFAULT
        shared.win.create_source_rows()

    def reset_app(self, *_args: Any) -> None:
        rmtree(shared.data_dir / "sofl", True)
        rmtree(shared.config_dir / "sofl", True)
        rmtree(shared.cache_dir / "sofl", True)

        for key in (
            (settings_schema_source := Gio.SettingsSchemaSource.get_default())
            .lookup(shared.APP_ID, True)
            .list_keys()
        ):
            shared.schema.reset(key)
        for key in settings_schema_source.lookup(
            shared.APP_ID + ".State", True
        ).list_keys():
            shared.state_schema.reset(key)

        shared.win.get_application().quit()

    def update_source_action_row_paths(self, source: Source) -> None:
        """Set the dir subtitle for a source's action rows"""
        for location_name, location in source.locations._asdict().items():
            # Get the action row to subtitle
            action_row = getattr(
                self, f"{source.source_id}_{location_name}_action_row", None
            )
            if not action_row:
                continue

            subtitle = str(Path(shared.schema.get_string(location.schema_key)))

            if platform == "linux":
                # Remove the path prefix if picked via Flatpak portal
                subtitle = re.sub("/run/user/\\d*/doc/.*/", "", subtitle)

                # Replace the home directory with "~"
                subtitle = re.sub(f"^{str(shared.home)}", "~", subtitle)

            action_row.set_subtitle(subtitle)

    def resolve_locations(self, source: Source) -> None:
        """Resolve locations and add a warning if location cannot be found"""

        for location_name, location in source.locations._asdict().items():
            action_row = getattr(
                self, f"{source.source_id}_{location_name}_action_row", None
            )
            if not action_row:
                continue

            try:
                location.resolve()

            except UnresolvableLocationError:
                title = _("Installation Not Found")
                description = _("Select a valid directory")
                format_start = '<span rise="12pt"><b><big>'
                format_end = "</big></b></span>\n"

                popover = Gtk.Popover(
                    focusable=True,
                    child=(
                        Gtk.Label(
                            label=format_start + title + format_end + description,
                            use_markup=True,
                            wrap=True,
                            max_width_chars=50,
                            halign=Gtk.Align.CENTER,
                            valign=Gtk.Align.CENTER,
                            justify=Gtk.Justification.CENTER,
                            margin_top=9,
                            margin_bottom=9,
                            margin_start=12,
                            margin_end=12,
                        )
                    ),
                )

                popover.update_property(
                    (Gtk.AccessibleProperty.LABEL,), (title + description,)
                )

                def set_a11y_label(widget: Gtk.Popover) -> None:
                    self.set_focus(widget)

                popover.connect("show", set_a11y_label)

                menu_button = Gtk.MenuButton(
                    icon_name="dialog-warning-symbolic",
                    valign=Gtk.Align.CENTER,
                    popover=popover,
                    tooltip_text=_("Warning"),
                )
                menu_button.add_css_class("warning")

                action_row.add_prefix(menu_button)
                self.warning_menu_buttons[source.source_id] = menu_button

    def init_source_row(self, source: Source) -> None:
        """Initialize a preference row for a source class"""

        def set_dir(_widget: Any, result: Gio.Task, location_name: str) -> None:
            """Callback called when a dir picker button is clicked"""
            try:
                path = Path(self.file_chooser.select_folder_finish(result).get_path())
            except GLib.Error as e:
                logging.error("Error selecting directory: %s", e.message)
                return

            # Good picked location
            location = source.locations._asdict()[location_name]
            if location.check_candidate(path):
                shared.schema.set_string(location.schema_key, str(path))
                self.update_source_action_row_paths(source)
                if self.warning_menu_buttons.get(source.source_id):
                    action_row = getattr(
                        self, f"{source.source_id}_{location_name}_action_row", None
                    )
                    action_row.remove(  # type: ignore
                        self.warning_menu_buttons[source.source_id]
                    )
                    self.warning_menu_buttons.pop(source.source_id)
                logging.debug("User-set value for %s is %s", location.schema_key, path)

            # Bad picked location, inform user
            else:
                title = _("Invalid Directory")
                dialog = create_dialog(
                    self,
                    title,
                    location.invalid_subtitle.format(source.name),
                    "choose_folder",
                    _("Set Location"),
                )

                def on_response(widget: Any, response: str) -> None:
                    if response == "choose_folder":
                        self.choose_folder(widget, set_dir, location_name)

                dialog.connect("response", on_response)

        # Bind expander row activation to source being enabled
        expander_row = getattr(self, f"{source.source_id}_expander_row")
        shared.schema.bind(
            source.source_id,
            expander_row,
            "enable-expansion",
            Gio.SettingsBindFlags.DEFAULT,
        )

        # Connect dir picker buttons
        for location_name in source.locations._asdict():
            button = getattr(
                self, f"{source.source_id}_{location_name}_file_chooser_button", None
            )
            if button is not None:
                button.connect("clicked", self.choose_folder, set_dir, location_name)

        # Set the source row subtitles
        self.resolve_locations(source)
        self.update_source_action_row_paths(source)

    def check_umu_availability(self) -> bool:
        """Check if umu-run is available on the system

        Returns:
            bool: True if umu-run is available, False otherwise
        """
        # Check Flatpak path first
        flatpak_umu_path = f"{os.getenv('FLATPAK_DEST')}/bin/umu/umu-run"
        if os.path.exists("/.flatpak-info") and os.path.isfile(flatpak_umu_path):
            return True

        # Check PATH and vendor path
        import shutil

        path_candidate = shutil.which("umu-run")
        vendor_candidate = "/usr/share/sofl/umu/umu-run"

        return bool(path_candidate or os.path.isfile(vendor_candidate))

    def setup_launcher_combo(self) -> None:
        """Setup launcher selection combo box, hiding UMU if not available"""
        umu_available = self.check_umu_availability()

        if umu_available:
            # Both launchers available
            launcher_options = ["Steam API", "UMU Launcher"]
            self.online_fix_launcher_combo.set_sensitive(True)
            self.online_fix_umu_banner_box.set_visible(False)
        else:
            # Only Steam API available, disable combo and show info banner
            launcher_options = ["Steam API"]
            self.online_fix_launcher_combo.set_sensitive(False)
            self.online_fix_umu_banner_box.set_visible(True)

        launcher_model = Gtk.StringList.new(launcher_options)
        self.online_fix_launcher_combo.set_model(launcher_model)

        # Get current selection, but ensure it's valid
        try:
            current_launcher = shared.schema.get_int("online-fix-launcher-type")
            if not umu_available and current_launcher == 1:
                # Reset to Steam API if UMU was selected but is not available
                current_launcher = 0
                shared.schema.set_int("online-fix-launcher-type", current_launcher)
        except GLib.Error:
            current_launcher = 0

        self.online_fix_launcher_combo.set_selected(current_launcher)
        self.online_fix_launcher_combo.connect(
            "notify::selected", self.on_launcher_changed
        )

    def setup_online_fix_settings(self) -> None:
        """Setup parameters for Online-Fix"""
        # Check for the key in settings
        try:
            # Try to get the value if the key exists
            current_path = shared.schema.get_string("online-fix-install-path")
        except GLib.Error as e:
            # If the key does not exist, set the default value
            default_path = str(Path(shared.home) / "Games" / "Online-Fix")
            shared.schema.set_string("online-fix-install-path", default_path)
            current_path = default_path
            logging.warning(
                f"Online-Fix install path not found, using default: {default_path}"
            )

        # Fill the field with the last saved path
        self.online_fix_entry_row.set_text(current_path)

        # Handler for manual path change
        def online_fix_path_changed(*_args: Any) -> None:
            shared.schema.set_string(
                "online-fix-install-path", self.online_fix_entry_row.get_text()
            )

        self.online_fix_entry_row.connect("changed", online_fix_path_changed)

        # Handler for the folder selection button
        self.online_fix_file_chooser_button.connect(
            "clicked", self.online_fix_path_browse_handler
        )

        # Setup launcher selection
        self.setup_launcher_combo()

        # Get available Proton versions
        proton_versions = self.get_proton_versions()

        # Setup Proton version selection for Steam API
        self.setup_proton_combo(
            self.online_fix_proton_combo, proton_versions, "online-fix-proton-version"
        )

        # Setup Proton version selection for UMU Launcher
        self.setup_proton_combo(
            self.online_fix_umu_proton_combo,
            proton_versions,
            "online-fix-umu-proton-version",
        )

        # Setup auto patch switch
        shared.schema.bind(
            "online-fix-auto-patch",
            self.online_fix_auto_patch_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )

        # Connect auto-patch switch to show/hide manual options
        self.online_fix_auto_patch_switch.connect(
            "notify::active", self.on_auto_patch_changed
        )

        # Setup DLL overrides
        self.online_fix_dll_override_entry.set_text(
            shared.schema.get_string("online-fix-dll-overrides")
        )
        self.online_fix_dll_override_entry.connect(
            "changed", self.on_dll_overrides_changed
        )

        # Setup manual patches
        shared.schema.bind(
            "online-fix-steam-appid-patch",
            self.online_fix_steam_appid_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )

        shared.schema.bind(
            "online-fix-steamfix64-patch",
            self.online_fix_patch_steam_fix_64,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )

        # Set initial visibility
        self.on_auto_patch_changed(self.online_fix_auto_patch_switch, None)
        self.on_launcher_changed(self.online_fix_launcher_combo, None)

    def setup_proton_combo(
        self, combo: Adw.ComboRow, proton_versions: list[str], schema_key: str
    ) -> None:
        """Setup Proton version selection combo box"""
        # Create model for combo box
        proton_model = Gtk.StringList.new([version for version in proton_versions])
        combo.set_model(proton_model)

        # Get current selection from settings
        try:
            current_proton = shared.schema.get_string(schema_key)
        except GLib.Error as e:
            # If setting doesn't exist, use the first available proton version
            if proton_versions:
                current_proton = proton_versions[0]
            else:
                # Fallback defaults if no versions found
                current_proton = (
                    "GE-Proton9-26"
                    if schema_key == "online-fix-proton-version"
                    else "GE-Proton10-3"
                )
            shared.schema.set_string(schema_key, current_proton)

        # Find index of current selection
        selected_idx = 0
        for idx, version in enumerate(proton_versions):
            if version == current_proton:
                selected_idx = idx
                break

        # Set selected item
        combo.set_selected(selected_idx)

        # Connect signal for selection change
        combo.connect(
            "notify::selected", lambda c, _: self.on_proton_changed(c, schema_key)
        )

    def on_proton_changed(self, combo: Adw.ComboRow, schema_key: str) -> None:
        """Handler for Proton version change"""
        selected_idx = combo.get_selected()
        if selected_idx >= 0:
            model = combo.get_model()
            if model and selected_idx < model.get_n_items():
                selected_version = model.get_string(selected_idx)
                shared.schema.set_string(schema_key, selected_version)
                logging.info(
                    f"Proton version set to: {selected_version} for {schema_key}"
                )

    def get_proton_versions(self) -> list[str]:
        """Get available Proton versions from compatibility.d directory"""
        proton_path = Path(
            os.path.expanduser("~/.local/share/Steam/compatibilitytools.d")
        )
        versions = []

        # Default versions if no others found
        default_versions = ["GE-Proton10-3", "GE-Proton9-26", "Proton-8.0"]

        if proton_path.exists() and proton_path.is_dir():
            for item in proton_path.iterdir():
                if item.is_dir() and (
                    item.name.startswith("GE-Proton") or item.name.startswith("Proton")
                ):
                    versions.append(item.name)

        # If no versions found, add defaults
        if not versions:
            versions = default_versions

        # Sort versions
        versions.sort(reverse=True)

        return versions

    def on_auto_patch_changed(self, switch: Adw.SwitchRow, _param: Any) -> None:
        """Show/hide manual settings based on auto-patch switch"""
        is_auto = switch.get_active()
        self.online_fix_patches_group.set_visible(not is_auto)

    def on_launcher_changed(self, combo: Adw.ComboRow, _param: Any) -> None:
        """Handler for launcher type change"""
        launcher_type = combo.get_selected()

        # Check if UMU is available when trying to select it
        if launcher_type == 1 and not self.check_umu_availability():
            # Reset to Steam API if UMU is not available
            launcher_type = 0
            combo.set_selected(0)
            self.add_toast(
                Adw.Toast.new(
                    _("UMU Launcher is not available. Please install umu-launcher.")
                )
            )

        shared.schema.set_int("online-fix-launcher-type", launcher_type)

        # Show appropriate Proton selection control based on launcher type
        # 0 = Steam API
        # 1 = UMU Launcher
        self.online_fix_proton_combo.set_visible(launcher_type == 0)
        self.online_fix_umu_proton_combo.set_visible(launcher_type == 1)

    def on_dll_overrides_changed(self, entry: Adw.EntryRow) -> None:
        """Handler for DLL overrides change"""
        shared.schema.set_string("online-fix-dll-overrides", entry.get_text())

    def online_fix_path_browse_handler(self, *_args):
        """Choose directory for Online-Fix games installation"""

        def set_online_fix_dir(_widget: Any, result: Gio.Task) -> None:
            try:
                path = Path(self.file_chooser.select_folder_finish(result).get_path())
                shared.schema.set_string("online-fix-install-path", str(path))
                self.online_fix_entry_row.set_text(str(path))
            except GLib.Error as e:
                logging.debug("Error selecting folder for Online-Fix: %s", e)

        self.file_chooser.select_folder(shared.win, None, set_online_fix_dir)
