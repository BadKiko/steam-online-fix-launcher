# SOFL Changelog

## [v0.0.3.3a] - 2025-09-01

### Major Changes

- **Removed Umu Launcher Integration**: Completely removed Umu Launcher support and related Proton version settings
- **Enhanced Stability**: Improved overall application stability and performance
- **Build System Overhaul**: Refactored build configuration for better maintainability

### Bug Fixes

- Fixed various UI styling inconsistencies and layout issues
- Resolved build process reliability problems
- Fixed package dependency resolution issues
- Improved error handling throughout the application

### Documentation Improvements

- **Enhanced README**: Completely rewritten with better project description, features, and installation instructions\
- **Contributing Guidelines**: Created detailed CONTRIBUTING.md and CONTRIBUTING_RU.md with step-by-step instructions
- **Project Structure**: Added clear code architecture overview and development requirements

### Development Tools

- **Build Scripts**: Enhanced Flatpak build scripts with stable/dev version support
- **Development Scripts**: Added new development build scripts for faster iteration\

### UI/UX Improvements

- **Game Type Selection**: Added new "Game Type" combo row for distinguishing Online-Fix and Regular games
- **Dialog Enhancements**: Improved details dialog and preferences dialog styling
- **CSS Cleanup**: Better organized and documented stylesheets

### Removed Features

- Umu Launcher integration and Proton version settings
- Outdated documentation files
- Legacy configuration keys

## [v0.0.3.2a] - 2025-08-27

- Fixed #26 @BadKiko
- Fixed #27 @BadKiko

## [v0.0.3.1a] - 2025-08-26

- Fxed #24
- Fixed online-fix removing
- Added select on adding games

## [v0.0.3] - 2025-08-25

### New Features

- Enhanced CI/CD workflow with flexible release body generation
- Added support for manual release body input via workflow dispatch
- Automatic changelog generation from git commits
- Improved package building for multiple Linux distributions

### Bug Fixes

- Fixed Flatpak manifest blueprint-compiler version handling
- Resolved Arch Linux package build issues
- Improved Debian package dependency handling

### Other Changes

- Updated build scripts for better error handling
- Enhanced documentation and installation instructions
- Improved workflow reliability and artifact management

## [v0.0.2] - 2025-06-25

### New Features

- Support for multiple game launchers integration
- SteamGridDB integration for automatic cover art
- Online-fix game support with comprehensive settings

### Bug Fixes

- Fixed various launcher integration issues
- Resolved cover art download problems
- Improved error handling for network requests

## [v0.0.1] - 2025-04-25

### New Features

- Initial release with basic functionality
- GTK4 + LibAdwaita UI
- Basic game library management
- Flatpak packaging support

### Installation

- Flatpak support
- Debian/Ubuntu packages
- Arch Linux PKGBUILD

---

_This changelog is automatically parsed by the CI/CD workflow for release generation._
