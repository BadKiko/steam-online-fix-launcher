# 🤝 Contributing to SOFL

Hi! 👋 Thanks for wanting to help improve SOFL. Here's a simple guide to get started.

<p align="center">
  <a href="CONTRIBUTING_RU.md"><img src="https://img.shields.io/badge/🇷🇺-Russian-blue" alt="Russian"></a>
  <a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/🇺🇸-English-red" alt="English"></a>
</p>

---

## 🚀 Quick Start

### Fork and Clone

```bash
# 1. Fork the repository on GitHub
# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/steam-online-fix-launcher.git
cd steam-online-fix-launcher

# 3. Create a working branch
git checkout -b my-feature

# 4. Run the application for development
./scripts/dev.sh
```

---

## 🔄 Development

### Creating a Pull Request

1. **Make changes** in your code
2. **Test** that everything works: `./scripts/dev.sh`
3. **Commit changes**:
   ```bash
   git add .
   git commit -m "Brief description of changes"
   ```
4. **Push to your fork**:
   ```bash
   git push origin my-feature
   ```
5. **Create a Pull Request** on GitHub

### Simple Rules

- Write clear commit messages
- Test changes before submitting
- Add a brief description for new features
- Follow the existing code style

---

## 🐛 Bugs and Features

### Report a Bug

Use GitHub Issues with the template:

- What were you doing?
- What did you expect to see?
- What happened instead?
- Your system (Linux distribution, version)

### Suggest a New Feature

Describe in the Issue:

- What will it do?
- Why is it useful?
- How should it work?

---

## 🛠️ Working with Code

### Architecture

```
sofl/
├── main.py          # Application launch
├── window.py        # Main window
├── game.py          # Games
├── store/           # Data storage
├── importer/        # Game import
├── dialogs/         # Dialogs
└── utils/           # Utilities
```

### Requirements

- Python 3.10+
- GTK4 + LibAdwaita
- Meson for building

---

## 🌐 Translations

### Add a New Language

```bash
# 1. Add language code to po/LINGUAS
echo "ru" >> po/LINGUAS

# 2. Create .po file
msginit --input=po/sofl.pot --locale=ru --output=po/ru.po

# 3. Translate in Poedit or text editor
# 4. Create Pull Request
```

### Update Translations

```bash
meson compile sofl-pot -C builddir
meson compile sofl-update-po -C builddir
```

---

## 📝 Code and Commits

### Code Style

We use Black for formatting:

- Maximum 88 characters per line
- UTF-8 encoding
- 4 spaces indentation

### Commit Messages

The project uses a tagging system for commits

[AMR] - A-Added, M-Modified, R-Removed
So when adding new files and editing old ones, there will be a tag before the commit [AM].
Examples:

- [A] added file `new_feature.py`
- [M] changed file `README.md`
- [R] removed file `old_script.py`

## 🙏 Thanks

Thanks for contributing to SOFL! Together we're making Linux better for gamers. 🎮
