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
    online_fix_proton_entry: Adw.EntryRow = Gtk.Template.Child()

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
            logging.warning(f"Online-Fix install path not found, using default: {default_path}")
        
        # Fill the field with the last saved path
        self.online_fix_entry_row.set_text(current_path)
        
        # Handler for manual path change
        def online_fix_path_changed(*_args: Any) -> None:
            shared.schema.set_string("online-fix-install-path", self.online_fix_entry_row.get_text())
        
        self.online_fix_entry_row.connect("changed", online_fix_path_changed)
        
        # Handler for the folder selection button
        self.online_fix_file_chooser_button.connect("clicked", self.online_fix_path_browse_handler)

        # Setup launcher selection
        launcher_model = Gtk.StringList.new(["Steam API", "UMU Launcher"])
        self.online_fix_launcher_combo.set_model(launcher_model)
        self.online_fix_launcher_combo.set_selected(shared.schema.get_int("online-fix-launcher-type"))
        self.online_fix_launcher_combo.connect("notify::selected", self.on_launcher_changed)

        # Setup Proton version field
        try:
            current_proton = shared.schema.get_string("online-fix-proton-version")
            self.online_fix_proton_entry.set_text(current_proton)
        except GLib.Error as e:
            default_proton = "GE-Proton9-26"
            shared.schema.set_string("online-fix-proton-version", default_proton)
            self.online_fix_proton_entry.set_text(default_proton)
            

        # Handler for Proton version change
        def on_proton_version_changed(*_args: Any) -> None:
            shared.schema.set_string("online-fix-proton-version", self.online_fix_proton_entry.get_text())
            
        self.online_fix_proton_entry.connect("changed", on_proton_version_changed)
        
        # Setup auto patch switch
        shared.schema.bind(
            "online-fix-auto-patch",
            self.online_fix_auto_patch_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        
        # Connect auto-patch switch to show/hide manual options
        self.online_fix_auto_patch_switch.connect("notify::active", self.on_auto_patch_changed)
        
        # Setup DLL overrides
        self.online_fix_dll_override_entry.set_text(shared.schema.get_string("online-fix-dll-overrides"))
        self.online_fix_dll_override_entry.connect("changed", self.on_dll_overrides_changed)
        
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

    def on_auto_patch_changed(self, switch: Adw.SwitchRow, _param: Any) -> None:
        """Show/hide manual settings based on auto-patch switch"""
        is_auto = switch.get_active()
        self.online_fix_patches_group.set_visible(not is_auto)

    def on_launcher_changed(self, combo: Adw.ComboRow, _param: Any) -> None:
        """Handler for launcher type change"""
        launcher_type = combo.get_selected()
        shared.schema.set_int("online-fix-launcher-type", launcher_type)
        
        # Show Proton version field only when Steam launcher is selected (type 0)
        self.online_fix_proton_entry.set_visible(launcher_type == 0)

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
