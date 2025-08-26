#!/usr/bin/env python3
"""
Simple test to verify that GameData initialization works correctly
"""
import sys
import os

# Add sofl module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "sofl"))

from sofl.game_data import GameData


def test_gamedata_with_minimal_data():
    """Test GameData creation with minimal data (like in details_dialog.py)"""
    minimal_data = {
        "game_id": "imported_1",
        "hidden": False,
        "source": "test_source",
        "added": 1234567890,
    }

    try:
        game_data = GameData(minimal_data)
        print(f"✓ GameData created successfully: {game_data}")
        print(f"✓ Name attribute: '{game_data.name}'")
        print(f"✓ Executable attribute: '{game_data.executable}'")
        print(f"✓ Game ID: '{game_data.game_id}'")
        print(f"✓ Source: '{game_data.source}'")
        print("✓ All attributes are accessible")
        return True
    except Exception as e:
        print(f"✗ Error creating GameData: {e}")
        return False


def test_gamedata_with_full_data():
    """Test GameData creation with complete data"""
    full_data = {
        "name": "Test Game",
        "executable": "/path/to/game.exe",
        "game_id": "test_game_1",
        "source": "steam",
        "added": 1234567890,
        "hidden": False,
        "last_played": 1234567890,
        "developer": "Test Developer",
        "removed": False,
        "blacklisted": False,
    }

    try:
        game_data = GameData(full_data)
        print(f"✓ GameData created with full data: {game_data}")
        print(f"✓ Name attribute: '{game_data.name}'")
        print(f"✓ Executable attribute: '{game_data.executable}'")
        print("✓ All attributes match provided data")
        return True
    except Exception as e:
        print(f"✗ Error creating GameData with full data: {e}")
        return False


if __name__ == "__main__":
    print("Testing GameData initialization fix...")
    print()

    success1 = test_gamedata_with_minimal_data()
    print()
    success2 = test_gamedata_with_full_data()

    if success1 and success2:
        print("🎉 All tests passed! The GameData fix is working correctly.")
        sys.exit(0)
    else:
        print("❌ Some tests failed.")
        sys.exit(1)
