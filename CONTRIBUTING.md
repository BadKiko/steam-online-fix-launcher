# 🤝 Contributing to SOFL

We welcome contributions to SOFL! Whether you're fixing bugs, adding features, improving documentation, or helping with translations, your help is appreciated.

## 📖 Quick Start

### For Contributors

If you're new to contributing or want detailed guidance, check out our comprehensive [**Russian Contributor Guide**](CONTRIBUTING_RU.md) with step-by-step instructions.

### For Developers

```bash
# Clone and setup
git clone https://github.com/BadKiko/steam-online-fix-launcher.git
cd steam-online-fix-launcher

# Run in development mode
./scripts/dev.sh
```

## 🎯 Ways to Contribute

### 🐛 Bug Fixes

- Fork the repository
- Create a branch: `git checkout -b fix/issue-description`
- Make your changes
- Test thoroughly
- Create a Pull Request

### ✨ New Features

- [Create an issue](https://github.com/BadKiko/steam-online-fix-launcher/issues/new) to discuss
- Join [Discord](https://discord.gg/4KSFh3AmQR) or [Matrix](https://matrix.to/#/#sofl:matrix.org)
- Follow the standard development process

### 🌐 Translations

- **Weblate**: [Translate on Weblate](https://hosted.weblate.org/engage/sofl/)
- **Manual**: Follow our [detailed translation guide](CONTRIBUTING_RU.md#переводы)

### 📚 Documentation

- Improve existing docs
- Add new documentation
- Translate docs to other languages

## 🛠️ Development Setup

### Quick Development

```bash
# Smart development mode (recommended)
./scripts/dev.sh smart

# Full cycle: setup + build + install + run
./scripts/dev.sh all

# Flatpak development
cd packaging/flatpak && ./dev.sh dev
```

### Manual Setup

```bash
# System dependencies
sudo apt install meson ninja-build blueprint-compiler
sudo apt install libgtk-4-dev libadwaita-1-dev

# Python dependencies
pip install requests pillow rarfile vdf

# Build
meson setup builddir
ninja -C builddir install
```

## 📝 Code Style

We use automated code formatting:

- **Black** for Python formatting
- **isort** for import sorting
- **Pylint** for linting

### VSCode Configuration

```json
{
  "python.formatting.provider": "none",
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "isort.args": ["--profile", "black"]
}
```

## 🔄 Development Workflow

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** your changes
5. **Commit** with clear messages
6. **Push** to your fork
7. **Create** a Pull Request

## 📋 Pull Request Guidelines

- Use descriptive titles
- Reference related issues
- Include screenshots for UI changes
- Test on multiple environments
- Update documentation if needed
- Follow code style guidelines

## 🆘 Need Help?

- 📖 **[Detailed Russian Guide](CONTRIBUTING_RU.md)**
- 💬 **Discord**: https://discord.gg/4KSFh3AmQR
- 📧 **Matrix**: #sofl:matrix.org
- 🐛 **Issues**: For bugs and feature requests

## 🙏 Recognition

Contributors are recognized in:

- AUTHORS file
- Release notes
- Special acknowledgments section
- Community events and giveaways

---

**Thank you for contributing to SOFL!** 🚀
