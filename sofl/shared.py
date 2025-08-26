# Temporary shared.py for testing
from enum import IntEnum, auto
from os import getenv
from pathlib import Path


class AppState(IntEnum):
    DEFAULT = auto()
    LOAD_FROM_DISK = auto()
    IMPORT = auto()
    REMOVE_ALL_GAMES = auto()
    UNDO_REMOVE_ALL_GAMES = auto()


APP_ID = "org.badkiko.sofl"
VERSION = "0.0.3"
PREFIX = "/usr"
PROFILE = "release"
TIFF_COMPRESSION = "webp"
SPEC_VERSION = 1.5  # The version of the game_id.json spec


# Mock Gio.Settings for testing
class MockSettings:
    def __init__(self, app_id):
        self.app_id = app_id

    def get_boolean(self, key):
        return False

    def get_string(self, key):
        return ""

    def get_int(self, key):
        return 0


schema = MockSettings(APP_ID)
state_schema = MockSettings(APP_ID + ".State")

home = Path.home()
data_dir = Path.home() / ".local" / "share"
config_dir = Path.home() / ".config"
cache_dir = Path.home() / ".cache"

games_dir = data_dir / "sofl" / "games"
covers_dir = data_dir / "sofl" / "covers"

# Mock window for testing
win = None
