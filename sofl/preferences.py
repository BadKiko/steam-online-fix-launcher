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
import threading
from pathlib import Path
from shutil import rmtree
from sys import platform
from typing import Any, Callable, Optional
import os
import subprocess

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
from sofl.proton.proton_manager import ProtonManager
from sofl.store.managers.sgdb_manager import SgdbManager
from sofl.utils.create_dialog import create_dialog


@Gtk.Template(resource_path=shared.PREFIX + "/gtk/preferences.ui")
class SOFLPreferences(Adw.PreferencesDialog):
    __gtype_name__ = "SOFLPreferences"

    general_page: Adw.PreferencesPage = Gtk.Template.Child()
    import_page: Adw.PreferencesPage = Gtk.Template.Child()
    proton_page: Adw.PreferencesPage = Gtk.Template.Child()
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

    lutris_expander_row: Adw.ExpanderRow = Gtk.Template.Child()
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

    online_fix_auto_patch_switch: Adw.SwitchRow = Gtk.Template.Child()
    online_fix_dll_override_entry: Adw.EntryRow = Gtk.Template.Child()
    online_fix_dll_group: Adw.PreferencesGroup = Gtk.Template.Child()
    online_fix_patches_group: Adw.PreferencesGroup = Gtk.Template.Child()
    online_fix_steam_appid_switch: Adw.SwitchRow = Gtk.Template.Child()
    online_fix_patch_steam_fix_64: Adw.SwitchRow = Gtk.Template.Child()
    online_fix_proton_combo: Adw.ComboRow = Gtk.Template.Child()

    # Proton Manager
    proton_manager_group: Adw.PreferencesGroup = Gtk.Template.Child()

    removed_games: set[Game] = set()
    warning_menu_buttons: dict = {}
    
    # Download progress tracking
    active_downloads: dict = {}  # {version_name: {'row': row, 'progress_bar': bar, 'cancel_button': btn}}

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

        # Proton Manager setup (must be before Online-Fix setup)
        self.setup_proton_manager()
        
        # Online-Fix setup
        self.setup_online_fix_settings()

        # Windows runs games natively: Proton and Wine DLL overrides don't apply
        if platform == "win32":
            self.remove(self.proton_page)
            self.online_fix_proton_combo.set_visible(False)
            self.online_fix_dll_group.set_visible(False)

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

        # Synchronize theme switch with force-theme setting
        theme = shared.schema.get_string("force-theme")
        self.force_theme_switch.set_active(theme == "dark")

        def on_theme_switch(row, _param):
            shared.schema.set_string(
                "force-theme", "dark" if row.get_active() else "light"
            )
            # (optional) apply theme immediately:
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

        # Get available Proton versions
        proton_versions = self.get_proton_versions()

        # Setup Proton version selection for Steam API
        self.setup_proton_combo(
            self.online_fix_proton_combo, proton_versions, "online-fix-proton-version"
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

    def setup_proton_combo(
        self, combo: Adw.ComboRow, proton_versions: list[str], schema_key: str
    ) -> None:
        """Setup Proton version selection combo box"""
        # Create model for combo box
        proton_model = Gtk.StringList.new(list(proton_versions))
        combo.set_model(proton_model)
        # Get current selection from settings
        try:
            current_proton = shared.schema.get_string(schema_key)
        except GLib.Error:
            # If setting doesn't exist, pick first available (if any) and persist
            if proton_versions:
                current_proton = proton_versions[0]
                shared.schema.set_string(schema_key, current_proton)
            else:
                current_proton = ""
        # Find index of current selection
        selected_idx = 0
        found = False
        for idx, version in enumerate(proton_versions):
            if version == current_proton:
                selected_idx = idx
                found = True
                break
        # Set selected item
        combo.set_selected(selected_idx)
        # Connect signal for selection change
        combo.connect(
            "notify::selected", lambda c, _: self.on_proton_changed(c, schema_key)
        )
        # If schema had a stale/non-existent value, align it with UI selection
        if proton_versions and not found:
            shared.schema.set_string(schema_key, proton_versions[selected_idx])

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
        # Use ProtonManager if available, otherwise fallback to old method
        if hasattr(self, 'proton_manager_instance'):
            return self.proton_manager_instance.get_installed_versions()
        
        # Fallback method - use same logic as ProtonManager
        home = Path.home()
        steam_paths = [
            home / ".local/share/Steam/compatibilitytools.d",
            home / ".steam/root/compatibilitytools.d",
            home / ".steam/steam/compatibilitytools.d"
        ]
        
        versions = []
        
        # Check all possible paths
        for proton_path in steam_paths:
            if proton_path.exists() and proton_path.is_dir():
                try:
                    for item in proton_path.iterdir():
                        if item.is_dir() and (
                            item.name.startswith("GE-Proton") or 
                            item.name.startswith("Proton")
                        ):
                            # Check if it's a valid Proton installation
                            proton_script = item / "proton"
                            if proton_script.exists() and proton_script.is_file():
                                versions.append(item.name)
                except Exception as e:
                    logging.error(f"[Preferences] Error reading {proton_path}: {e}")
        
        # Remove duplicates and sort
        versions = list(set(versions))
        versions.sort(reverse=True)
        
        return versions

    def on_auto_patch_changed(self, switch: Adw.SwitchRow, _param: Any) -> None:
        """Show/hide manual settings based on auto-patch switch"""
        is_auto = switch.get_active()
        self.online_fix_patches_group.set_visible(not is_auto)

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

    def setup_proton_manager(self) -> None:
        """Setup Proton Manager functionality"""
        self.proton_manager_instance = ProtonManager()
        self.setup_proton_manager_ui()
        self.refresh_proton_versions()
        # Update combo box with installed versions
        self.update_proton_combo()

    def setup_proton_manager_ui(self) -> None:
        """Setup Proton Manager UI components with simple accordion design"""
        # Create installed versions accordion
        self.proton_installed_expander = Adw.ExpanderRow()
        self.proton_installed_expander.set_title(_("Installed Versions"))
        self.proton_installed_expander.set_subtitle(_("Manage your downloaded Proton versions"))
        
        # Create available versions accordion
        self.proton_available_expander = Adw.ExpanderRow()
        self.proton_available_expander.set_title(_("Available Versions"))
        self.proton_available_expander.set_subtitle(_("Download the latest GE-Proton releases from GitHub"))
        
        # Add accordions to the group
        self.proton_manager_group.add(self.proton_installed_expander)
        self.proton_manager_group.add(self.proton_available_expander)
        
        # Store references to current children for proper cleanup
        self.proton_installed_children = []
        self.proton_available_children = []
        self.proton_loading_spinner = None

    def refresh_proton_versions(self) -> None:
        """Refresh both installed and available Proton versions"""
        self.refresh_installed_versions()
        self.refresh_available_versions()

    def refresh_installed_versions(self) -> None:
        """Refresh the list of installed Proton versions"""
        try:
            logging.info("[Preferences] Refreshing installed Proton versions...")
            installed_versions = self.proton_manager_instance.get_installed_versions()
            logging.info(f"[Preferences] Found {len(installed_versions)} installed versions: {installed_versions}")
            
            # Clear existing children from installed accordion
            for child in self.proton_installed_children:
                self.proton_installed_expander.remove(child)
            self.proton_installed_children.clear()
            
            if not installed_versions:
                # Show simple empty state
                empty_label = Gtk.Label()
                empty_label.set_text(_("No Proton versions installed"))
                empty_label.set_css_classes(["dim-label"])
                empty_label.set_margin_top(12)
                empty_label.set_margin_bottom(12)
                empty_label.set_margin_start(12)
                empty_label.set_margin_end(12)
                
                self.proton_installed_expander.add_row(empty_label)
                self.proton_installed_children.append(empty_label)
                return
            
            # Add each installed version
            for version in installed_versions:
                row = self.create_installed_version_row(version)
                self.proton_installed_expander.add_row(row)
                self.proton_installed_children.append(row)
                
        except Exception as e:
            logging.error(f"[Preferences] Error refreshing installed versions: {e}")

    def refresh_available_versions(self) -> None:
        """Refresh the list of available Proton versions"""
        try:
            logging.info("[Preferences] Refreshing available Proton versions...")
            
            # Clear existing children from available accordion
            for child in self.proton_available_children:
                self.proton_available_expander.remove(child)
            self.proton_available_children.clear()
            
            # Show simple loading state
            loading_box = Gtk.Box()
            loading_box.set_orientation(Gtk.Orientation.HORIZONTAL)
            loading_box.set_spacing(12)
            loading_box.set_margin_top(12)
            loading_box.set_margin_bottom(12)
            loading_box.set_margin_start(12)
            loading_box.set_margin_end(12)
            
            # Spinner
            spinner = Gtk.Spinner()
            spinner.start()
            self.proton_loading_spinner = spinner  # Save reference to stop later
            loading_box.append(spinner)
            
            # Loading label
            loading_label = Gtk.Label()
            loading_label.set_text(_("Loading available versions..."))
            loading_label.set_css_classes(["dim-label"])
            loading_box.append(loading_label)
            
            self.proton_available_expander.add_row(loading_box)
            self.proton_available_children.append(loading_box)
            
            # Fetch available versions in a separate thread
            def fetch_versions():
                try:
                    logging.info("[Preferences] Fetching available versions in thread...")
                    available_versions = self.proton_manager_instance.get_available_versions(force_refresh=True)
                    logging.info(f"[Preferences] Found {len(available_versions)} available versions")
                    GLib.idle_add(self.on_available_versions_loaded, available_versions)
                except Exception as e:
                    logging.error(f"[Preferences] Error in fetch thread: {e}")
                    GLib.idle_add(self.on_available_versions_error, str(e))
            
            thread = threading.Thread(target=fetch_versions)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            logging.error(f"[Preferences] Error refreshing available versions: {e}")

    def on_available_versions_loaded(self, versions: list) -> None:
        """Handle loaded available versions"""
        try:
            logging.info(f"[Preferences] Handling {len(versions)} loaded versions")
            
            # Stop the loading spinner
            if self.proton_loading_spinner:
                self.proton_loading_spinner.stop()
                self.proton_loading_spinner = None
            
            # Clear existing children from available accordion
            for child in self.proton_available_children:
                self.proton_available_expander.remove(child)
            self.proton_available_children.clear()
            
            if not versions:
                # Show simple empty state
                empty_label = Gtk.Label()
                empty_label.set_text(_("No versions available"))
                empty_label.set_css_classes(["dim-label"])
                empty_label.set_margin_top(12)
                empty_label.set_margin_bottom(12)
                empty_label.set_margin_start(12)
                empty_label.set_margin_end(12)
                
                self.proton_available_expander.add_row(empty_label)
                self.proton_available_children.append(empty_label)
                return
            
            # Add each available version
            for version_info in versions:
                logging.info(f"[Preferences] Creating row for version: {version_info.get('tag_name', 'unknown')}")
                row = self.create_available_version_row(version_info)
                self.proton_available_expander.add_row(row)
                self.proton_available_children.append(row)
                
        except Exception as e:
            logging.error(f"[Preferences] Error handling loaded versions: {e}")

    def on_available_versions_error(self, error: str) -> None:
        """Handle error loading available versions"""
        try:
            # Stop the loading spinner
            if self.proton_loading_spinner:
                self.proton_loading_spinner.stop()
                self.proton_loading_spinner = None
            
            # Clear existing children from available accordion
            for child in self.proton_available_children:
                self.proton_available_expander.remove(child)
            self.proton_available_children.clear()
            
            # Show simple error state
            error_box = Gtk.Box()
            error_box.set_orientation(Gtk.Orientation.HORIZONTAL)
            error_box.set_spacing(12)
            error_box.set_margin_top(12)
            error_box.set_margin_bottom(12)
            error_box.set_margin_start(12)
            error_box.set_margin_end(12)
            
            # Error icon
            error_icon = Gtk.Image()
            error_icon.set_from_icon_name("network-error-symbolic")
            error_icon.set_pixel_size(16)
            error_box.append(error_icon)
            
            # Error label
            error_label = Gtk.Label()
            error_label.set_text(_("Failed to load versions. Check your internet connection."))
            error_label.set_css_classes(["dim-label"])
            error_box.append(error_label)
            
            # Retry button
            retry_button = Gtk.Button()
            retry_button.set_icon_name("view-refresh-symbolic")
            retry_button.set_tooltip_text(_("Retry"))
            retry_button.set_css_classes(["flat"])
            retry_button.set_valign(Gtk.Align.CENTER)
            retry_button.connect("clicked", self.on_proton_retry_clicked)
            error_box.append(retry_button)
            
            self.proton_available_expander.add_row(error_box)
            self.proton_available_children.append(error_box)
            
        except Exception as e:
            logging.error(f"[Preferences] Error handling version load error: {e}")

    def create_installed_version_row(self, version: str) -> Adw.ActionRow:
        """Create a simple row for an installed Proton version"""
        row = Adw.ActionRow()
        row.set_title(version)
        row.set_subtitle(_("Installed"))
        
        # Delete button
        delete_button = Gtk.Button()
        delete_button.set_icon_name("user-trash-symbolic")
        delete_button.set_tooltip_text(_("Delete this version"))
        delete_button.set_css_classes(["destructive-action", "flat"])
        delete_button.set_valign(Gtk.Align.CENTER)
        delete_button.connect("clicked", self.on_delete_proton_version, version)
        
        row.add_suffix(delete_button)
        return row
    
    def create_version_info_section(self, version: str) -> Gtk.Widget:
        """Create detailed information section for a version"""
        info_box = Gtk.Box()
        info_box.set_orientation(Gtk.Orientation.VERTICAL)
        info_box.set_spacing(12)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_text(_("Version Information"))
        title_label.set_css_classes(["heading"])
        title_label.set_halign(Gtk.Align.START)
        info_box.append(title_label)
        
        # Info grid
        info_grid = Gtk.Grid()
        info_grid.set_column_spacing(16)
        info_grid.set_row_spacing(8)
        
        # Version name
        version_label = Gtk.Label()
        version_label.set_text(_("Version:"))
        version_label.set_css_classes(["dim-label"])
        version_label.set_halign(Gtk.Align.START)
        info_grid.attach(version_label, 0, 0, 1, 1)
        
        version_value = Gtk.Label()
        version_value.set_text(version)
        version_value.set_halign(Gtk.Align.START)
        info_grid.attach(version_value, 1, 0, 1, 1)
        
        # Installation path
        path_label = Gtk.Label()
        path_label.set_text(_("Location:"))
        path_label.set_css_classes(["dim-label"])
        path_label.set_halign(Gtk.Align.START)
        info_grid.attach(path_label, 0, 1, 1, 1)
        
        path_value = Gtk.Label()
        compat_path = self.proton_manager_instance.get_steam_compat_path()
        full_path = f"{compat_path}/{version}"
        path_value.set_text(full_path)
        path_value.set_css_classes(["monospace"])
        path_value.set_halign(Gtk.Align.START)
        path_value.set_selectable(True)
        info_grid.attach(path_value, 1, 1, 1, 1)
        
        # Status
        status_label = Gtk.Label()
        status_label.set_text(_("Status:"))
        status_label.set_css_classes(["dim-label"])
        status_label.set_halign(Gtk.Align.START)
        info_grid.attach(status_label, 0, 2, 1, 1)
        
        status_value = Gtk.Label()
        status_value.set_text(_("Installed and ready"))
        status_value.set_css_classes(["success"])
        status_value.set_halign(Gtk.Align.START)
        info_grid.attach(status_value, 1, 2, 1, 1)
        
        info_box.append(info_grid)
        
        return info_box
    
    def create_version_actions_section(self, version: str) -> Gtk.Widget:
        """Create actions section for a version"""
        actions_box = Gtk.Box()
        actions_box.set_orientation(Gtk.Orientation.VERTICAL)
        actions_box.set_spacing(12)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_text(_("Actions"))
        title_label.set_css_classes(["heading"])
        title_label.set_halign(Gtk.Align.START)
        actions_box.append(title_label)
        
        # Actions grid
        actions_grid = Gtk.Grid()
        actions_grid.set_column_spacing(12)
        actions_grid.set_row_spacing(8)
        
        # Open folder button
        open_button = Gtk.Button()
        open_button.set_label(_("Open Folder"))
        open_button.set_icon_name("folder-open-symbolic")
        open_button.set_css_classes(["pill"])
        open_button.connect("clicked", self.on_open_proton_folder, version)
        actions_grid.attach(open_button, 0, 0, 1, 1)
        
        # Test button
        test_button = Gtk.Button()
        test_button.set_label(_("Test Version"))
        test_button.set_icon_name("media-playback-start-symbolic")
        test_button.set_css_classes(["pill"])
        test_button.connect("clicked", self.on_test_proton_version, version)
        actions_grid.attach(test_button, 1, 0, 1, 1)
        
        # Delete button (larger, more prominent)
        delete_button = Gtk.Button()
        delete_button.set_label(_("Delete Version"))
        delete_button.set_icon_name("user-trash-symbolic")
        delete_button.set_css_classes(["destructive-action", "pill"])
        delete_button.connect("clicked", self.on_delete_proton_version, version)
        actions_grid.attach(delete_button, 0, 1, 2, 1)
        
        actions_box.append(actions_grid)
        
        return actions_box
    
    def on_open_proton_folder(self, button: Gtk.Button, version: str) -> None:
        """Open the Proton version folder in file manager"""
        try:
            import subprocess
            import os
            
            compat_path = self.proton_manager_instance.get_steam_compat_path()
            version_path = os.path.join(compat_path, version)
            
            if os.path.exists(version_path):
                # Try different file managers
                file_managers = ['xdg-open', 'nautilus', 'dolphin', 'thunar', 'pcmanfm']
                for fm in file_managers:
                    try:
                        subprocess.run([fm, version_path], check=True)
                        break
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue
                else:
                    # Fallback: show path in dialog
                    dialog = Adw.MessageDialog()
                    parent_window = self.get_root()
                    if isinstance(parent_window, Gtk.Window):
                        dialog.set_transient_for(parent_window)
                    dialog.set_heading(_("Proton Version Location"))
                    dialog.set_body(_("Path: {}").format(version_path))
                    dialog.add_response("ok", _("OK"))
                    dialog.set_default_response("ok")
                    dialog.present()
            else:
                self.add_toast(Adw.Toast.new(_("Version folder not found")))
                
        except Exception as e:
            logging.error(f"[Preferences] Error opening folder for {version}: {e}")
            self.add_toast(Adw.Toast.new(_("Failed to open folder")))
    
    def on_test_proton_version(self, button: Gtk.Button, version: str) -> None:
        """Test a Proton version by showing information"""
        try:
            dialog = Adw.MessageDialog()
            parent_window = self.get_root()
            if isinstance(parent_window, Gtk.Window):
                dialog.set_transient_for(parent_window)
            dialog.set_heading(_("Test Proton Version"))
            dialog.set_body(_("This would test the Proton version {} by running a simple compatibility check. This feature is not yet implemented.").format(version))
            dialog.add_response("ok", _("OK"))
            dialog.set_default_response("ok")
            dialog.present()
        except Exception as e:
            logging.error(f"[Preferences] Error testing version {version}: {e}")
            self.add_toast(Adw.Toast.new(_("Failed to test version")))

    def create_available_version_row(self, version_info: dict) -> Adw.ActionRow:
        """Create a simple row for an available Proton version"""
        row = Adw.ActionRow()
        tag_name = version_info.get("tag_name", "Unknown")
        name = version_info.get("name", tag_name)
        row.set_title(name)
        
        # Create subtitle with size and date
        size_bytes = version_info.get("size", 0)
        published_at = version_info.get("published_at", "")
        
        subtitle_parts = []
        if size_bytes > 0:
            size_mb = size_bytes / (1024 * 1024)
            subtitle_parts.append(_("Size: {:.1f} MB").format(size_mb))
        
        if published_at:
            try:
                from datetime import datetime
                date_obj = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                formatted_date = date_obj.strftime("%b %d, %Y")
                subtitle_parts.append(_("Released: {}").format(formatted_date))
            except:
                pass
        
        subtitle = " • ".join(subtitle_parts) if subtitle_parts else _("Available for download")
        row.set_subtitle(subtitle)
        
        # Create a box for buttons
        button_box = Gtk.Box()
        button_box.set_orientation(Gtk.Orientation.HORIZONTAL)
        button_box.set_spacing(6)
        
        # Progress bar (hidden by default)
        progress_bar = Gtk.ProgressBar()
        progress_bar.set_visible(False)
        progress_bar.set_valign(Gtk.Align.CENTER)
        progress_bar.set_hexpand(True)
        progress_bar.set_show_text(True)
        button_box.append(progress_bar)
        
        # Cancel button (hidden by default)
        cancel_button = Gtk.Button()
        cancel_button.set_icon_name("process-stop-symbolic")
        cancel_button.set_tooltip_text(_("Cancel download"))
        cancel_button.set_css_classes(["flat", "error"])
        cancel_button.set_valign(Gtk.Align.CENTER)
        cancel_button.set_visible(False)
        cancel_button.connect("clicked", self.on_cancel_download, version_info)
        button_box.append(cancel_button)
        
        # Download button
        download_button = Gtk.Button()
        download_button.set_icon_name("folder-download-symbolic")
        download_button.set_tooltip_text(_("Download and install this version"))
        download_button.set_css_classes(["flat"])
        download_button.set_valign(Gtk.Align.CENTER)
        download_button.connect("clicked", self.on_download_proton_version, version_info, progress_bar, cancel_button)
        button_box.append(download_button)
        
        row.add_suffix(button_box)
        
        # Store references for progress updates
        self.active_downloads[tag_name] = {
            'row': row,
            'progress_bar': progress_bar,
            'cancel_button': cancel_button,
            'download_button': download_button,
            'cancelled': False
        }
        
        return row
    
    def create_available_version_details(self, version_info: dict) -> Gtk.Widget:
        """Create detailed information section for an available version"""
        details_box = Gtk.Box()
        details_box.set_orientation(Gtk.Orientation.VERTICAL)
        details_box.set_spacing(12)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_text(_("Version Details"))
        title_label.set_css_classes(["heading"])
        title_label.set_halign(Gtk.Align.START)
        details_box.append(title_label)
        
        # Details grid
        details_grid = Gtk.Grid()
        details_grid.set_column_spacing(16)
        details_grid.set_row_spacing(8)
        
        # Version name
        name_label = Gtk.Label()
        name_label.set_text(_("Name:"))
        name_label.set_css_classes(["dim-label"])
        name_label.set_halign(Gtk.Align.START)
        details_grid.attach(name_label, 0, 0, 1, 1)
        
        name_value = Gtk.Label()
        name_value.set_text(version_info.get("name", "Unknown"))
        name_value.set_halign(Gtk.Align.START)
        details_grid.attach(name_value, 1, 0, 1, 1)
        
        # Size
        size_bytes = version_info.get("size", 0)
        if size_bytes > 0:
            size_label = Gtk.Label()
            size_label.set_text(_("Size:"))
            size_label.set_css_classes(["dim-label"])
            size_label.set_halign(Gtk.Align.START)
            details_grid.attach(size_label, 0, 1, 1, 1)
            
            size_mb = size_bytes / (1024 * 1024)
            size_value = Gtk.Label()
            size_value.set_text(_("{:.1f} MB").format(size_mb))
            size_value.set_halign(Gtk.Align.START)
            details_grid.attach(size_value, 1, 1, 1, 1)
        
        # Release date
        published_at = version_info.get("published_at", "")
        if published_at:
            date_label = Gtk.Label()
            date_label.set_text(_("Released:"))
            date_label.set_css_classes(["dim-label"])
            date_label.set_halign(Gtk.Align.START)
            details_grid.attach(date_label, 0, 2, 1, 1)
            
            try:
                from datetime import datetime
                date_obj = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                formatted_date = date_obj.strftime("%B %d, %Y")
                date_value = Gtk.Label()
                date_value.set_text(formatted_date)
                date_value.set_halign(Gtk.Align.START)
                details_grid.attach(date_value, 1, 2, 1, 1)
            except:
                pass
        
        # Download count
        download_count = version_info.get("download_count", 0)
        if download_count > 0:
            count_label = Gtk.Label()
            count_label.set_text(_("Downloads:"))
            count_label.set_css_classes(["dim-label"])
            count_label.set_halign(Gtk.Align.START)
            details_grid.attach(count_label, 0, 3, 1, 1)
            
            count_value = Gtk.Label()
            count_value.set_text(_("{:,}").format(download_count))
            count_value.set_halign(Gtk.Align.START)
            details_grid.attach(count_value, 1, 3, 1, 1)
        
        details_box.append(details_grid)
        
        return details_box
    
    def create_available_version_actions(self, version_info: dict) -> Gtk.Widget:
        """Create actions section for an available version"""
        actions_box = Gtk.Box()
        actions_box.set_orientation(Gtk.Orientation.VERTICAL)
        actions_box.set_spacing(12)
        
        # Title
        title_label = Gtk.Label()
        title_label.set_text(_("Actions"))
        title_label.set_css_classes(["heading"])
        title_label.set_halign(Gtk.Align.START)
        actions_box.append(title_label)
        
        # Actions grid
        actions_grid = Gtk.Grid()
        actions_grid.set_column_spacing(12)
        actions_grid.set_row_spacing(8)
        
        # Download button (larger, more prominent)
        download_button = Gtk.Button()
        download_button.set_label(_("Download & Install"))
        download_button.set_icon_name("folder-download-symbolic")
        download_button.set_css_classes(["suggested-action", "pill"])
        download_button.connect("clicked", self.on_download_proton_version, version_info)
        actions_grid.attach(download_button, 0, 0, 2, 1)
        
        # View on GitHub button
        github_button = Gtk.Button()
        github_button.set_label(_("View on GitHub"))
        github_button.set_icon_name("web-browser-symbolic")
        github_button.set_css_classes(["pill"])
        github_button.connect("clicked", self.on_view_github_release, version_info)
        actions_grid.attach(github_button, 0, 1, 1, 1)
        
        # Copy download link button
        copy_button = Gtk.Button()
        copy_button.set_label(_("Copy Link"))
        copy_button.set_icon_name("edit-copy-symbolic")
        copy_button.set_css_classes(["pill"])
        copy_button.connect("clicked", self.on_copy_download_link, version_info)
        actions_grid.attach(copy_button, 1, 1, 1, 1)
        
        actions_box.append(actions_grid)
        
        return actions_box
    
    def on_view_github_release(self, button: Gtk.Button, version_info: dict) -> None:
        """Open the GitHub release page in browser"""
        try:
            import subprocess
            html_url = version_info.get("html_url", "")
            if html_url:
                subprocess.run(["xdg-open", html_url], check=True)
            else:
                self.add_toast(Adw.Toast.new(_("GitHub URL not available")))
        except Exception as e:
            logging.error(f"[Preferences] Error opening GitHub release: {e}")
            self.add_toast(Adw.Toast.new(_("Failed to open GitHub page")))
    
    def on_copy_download_link(self, button: Gtk.Button, version_info: dict) -> None:
        """Copy download link to clipboard"""
        try:
            import subprocess
            
            # Find the download URL for the tar.gz file
            assets = version_info.get("assets", [])
            download_url = None
            
            for asset in assets:
                if asset.get("name", "").endswith(".tar.gz"):
                    download_url = asset.get("browser_download_url", "")
                    break
            
            if download_url:
                # Copy to clipboard using xclip or xsel
                try:
                    subprocess.run(["xclip", "-selection", "clipboard"], input=download_url, text=True, check=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    try:
                        subprocess.run(["xsel", "--clipboard", "--input"], input=download_url, text=True, check=True)
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        # Fallback: show in dialog
                        dialog = Adw.MessageDialog()
                        parent_window = self.get_root()
                        if isinstance(parent_window, Gtk.Window):
                            dialog.set_transient_for(parent_window)
                        dialog.set_heading(_("Download Link"))
                        dialog.set_body(_("Download URL: {}").format(download_url))
                        dialog.add_response("ok", _("OK"))
                        dialog.set_default_response("ok")
                        dialog.present()
                        return
                
                self.add_toast(Adw.Toast.new(_("Download link copied to clipboard")))
            else:
                self.add_toast(Adw.Toast.new(_("Download link not available")))
                
        except Exception as e:
            logging.error(f"[Preferences] Error copying download link: {e}")
            self.add_toast(Adw.Toast.new(_("Failed to copy link")))

    def on_delete_proton_version(self, button: Gtk.Button, version: str) -> None:
        """Handle delete Proton version button click with beautiful dialog"""
        # Create modern confirmation dialog
        dialog = Adw.MessageDialog()
        parent_window = self.get_root()
        if isinstance(parent_window, Gtk.Window):
            dialog.set_transient_for(parent_window)
        dialog.set_heading(_("Delete Proton Version"))
        dialog.set_body(_("Are you sure you want to delete {}? This action cannot be undone and you will need to download it again if needed.").format(version))
        dialog.set_body_use_markup(True)

        # Add responses
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("delete", _("Delete"))
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.connect("response", lambda d, r: self.handle_delete_response(r, version))
        dialog.present()

    def handle_delete_response(self, response: str, version: str) -> None:
        """Handle delete confirmation response"""
        if response != "delete":
            return
        
        try:
            success = self.proton_manager_instance.delete_version(version)
            if success:
                self.add_toast(Adw.Toast.new(_("{} deleted").format(version)))
                self.refresh_installed_versions()
                self.update_proton_combo()
            else:
                self.add_toast(Adw.Toast.new(_("Failed to delete {}").format(version)))
        except Exception as e:
            logging.error(f"[Preferences] Error deleting version {version}: {e}")
            self.add_toast(Adw.Toast.new(_("Error deleting version")))

    def on_download_progress(self, version_name: str, progress: float, message: str = "") -> None:
        """Handle download progress updates"""
        def update_ui():
            if version_name in self.active_downloads:
                download_info = self.active_downloads[version_name]
                progress_bar = download_info['progress_bar']
                progress_bar.set_fraction(progress)
                
                # Update text based on progress
                if progress < 1.0:
                    progress_bar.set_text(f"{int(progress * 100)}%")
                else:
                    progress_bar.set_text(_("Extracting..."))
        
        GLib.idle_add(update_ui)

    def on_download_proton_version(self, button: Gtk.Button, version_info: dict, progress_bar: Gtk.ProgressBar, cancel_button: Gtk.Button) -> None:
        """Handle download Proton version button click"""
        try:
            tag_name = version_info.get("tag_name", "Unknown")
            
            # Hide download button, show progress bar and cancel button
            button.set_visible(False)
            progress_bar.set_visible(True)
            progress_bar.set_fraction(0.0)
            progress_bar.set_text(_("Starting..."))
            cancel_button.set_visible(True)
            
            # Mark as not cancelled
            if tag_name in self.active_downloads:
                self.active_downloads[tag_name]['cancelled'] = False
            
            # Start download in separate thread
            def download_thread():
                try:
                    # Check if download was cancelled before starting
                    if tag_name in self.active_downloads and self.active_downloads[tag_name]['cancelled']:
                        GLib.idle_add(self.on_download_error, version_info, _("Download cancelled by user"), button, progress_bar, cancel_button)
                        return

                    # Create progress callback
                    def progress_callback(progress: float):
                        # Check if download was cancelled
                        if tag_name in self.active_downloads and self.active_downloads[tag_name]['cancelled']:
                            raise Exception(_("Download cancelled by user"))
                        self.on_download_progress(tag_name, progress)

                    success = self.proton_manager_instance.download_version(version_info, progress_callback)

                    # Check if download was cancelled after completion
                    if tag_name in self.active_downloads and self.active_downloads[tag_name]['cancelled']:
                        GLib.idle_add(self.on_download_error, version_info, _("Download cancelled by user"), button, progress_bar, cancel_button)
                    elif success:
                        GLib.idle_add(self.on_download_complete, version_info, button, progress_bar, cancel_button)
                    else:
                        GLib.idle_add(self.on_download_error, version_info, _("Download failed"), button, progress_bar, cancel_button)

                except Exception as e:
                    if "cancelled" in str(e).lower():
                        GLib.idle_add(self.on_download_error, version_info, str(e), button, progress_bar, cancel_button)
                    else:
                        logging.error(f"[Preferences] Error downloading version: {e}")
                        GLib.idle_add(self.on_download_error, version_info, str(e), button, progress_bar, cancel_button)
            
            thread = threading.Thread(target=download_thread, daemon=True)
            thread.start()
            
        except Exception as e:
            logging.error(f"[Preferences] Error starting download: {e}")
            self.add_toast(Adw.Toast.new(_("Failed to start download")))

    def on_download_complete(self, version_info: dict, button: Gtk.Button, progress_bar: Gtk.ProgressBar, cancel_button: Gtk.Button) -> None:
        """Handle successful download"""
        try:
            tag_name = version_info.get("tag_name", "Unknown")
            self.add_toast(Adw.Toast.new(_("Version {} downloaded successfully").format(tag_name)))
            self.refresh_installed_versions()
            self.update_proton_combo()
            
            # Hide progress bar and cancel button, show download button
            progress_bar.set_visible(False)
            cancel_button.set_visible(False)
            button.set_visible(True)
        except Exception as e:
            logging.error(f"[Preferences] Error handling download completion: {e}")

    def on_download_error(self, version_info: dict, error: str, button: Gtk.Button, progress_bar: Gtk.ProgressBar, cancel_button: Gtk.Button) -> None:
        """Handle download error"""
        try:
            tag_name = version_info.get("tag_name", "Unknown")
            logging.error(f"[Preferences] Download error for {tag_name}: {error}")

            # Check if it was cancelled
            if "cancel" in error.lower():
                self.add_toast(Adw.Toast.new(_("Download cancelled")))
            elif "failed" in error.lower():
                self.add_toast(Adw.Toast.new(_("Failed to download version")))
            else:
                self.add_toast(Adw.Toast.new(_("Download error: {}").format(error)))

            # Hide progress bar and cancel button, show download button
            progress_bar.set_visible(False)
            cancel_button.set_visible(False)
            button.set_visible(True)
        except Exception as e:
            logging.error(f"[Preferences] Error handling download error: {e}")
    
    def on_cancel_download(self, button: Gtk.Button, version_info: dict) -> None:
        """Handle cancel download button click"""
        try:
            tag_name = version_info.get("tag_name", "Unknown")
            if tag_name in self.active_downloads:
                self.active_downloads[tag_name]['cancelled'] = True
                logging.info(f"[Preferences] Download cancelled for {tag_name}")
        except Exception as e:
            logging.error(f"[Preferences] Error cancelling download: {e}")

    def on_proton_retry_clicked(self, button: Gtk.Button) -> None:
        """Handle retry button click"""
        self.refresh_available_versions()

    def update_proton_combo(self) -> None:
        """Update the Proton combo box with current installed versions"""
        try:
            logging.info("[Preferences] Updating Proton combo box...")
            installed_versions = self.proton_manager_instance.get_installed_versions()
            logging.info(f"[Preferences] Found {len(installed_versions)} installed versions: {installed_versions}")
            
            # Clear and rebuild the combo box model
            proton_model = Gtk.StringList.new(installed_versions)
            self.online_fix_proton_combo.set_model(proton_model)
            
            # Get current selection from settings
            try:
                current_proton = shared.schema.get_string("online-fix-proton-version")
                logging.info(f"[Preferences] Current selection in settings: {current_proton}")
            except GLib.Error:
                current_proton = ""
            
            # Find and set the current selection
            selected_idx = 0
            for idx, version in enumerate(installed_versions):
                if version == current_proton:
                    selected_idx = idx
                    break
            
            self.online_fix_proton_combo.set_selected(selected_idx)
            
            # If no versions available, show a warning
            if not installed_versions:
                logging.warning("[Preferences] No Proton versions found!")
                
        except Exception as e:
            logging.error(f"[Preferences] Error updating proton combo: {e}")
