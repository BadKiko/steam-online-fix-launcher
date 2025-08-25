# SOFL Release Workflow

## Overview

The CI/CD workflow now supports flexible release body generation with multiple options:

1. **Manual input** - Write custom release notes
2. **CHANGELOG.md** - Use structured changelog file
3. **Git commits** - Auto-generate from commit messages
4. **Auto mode** - Automatically choose best option

## Usage

### Manual Release Body

When triggering the workflow manually:

1. Go to **Actions** → **Build and Release Packages**
2. Click **Run workflow**
3. Fill in the inputs:
   - **Version**: Leave empty for auto-detection or specify manually
   - **Release body**: Write your custom release notes
   - **Release body source**: Select "auto" (or leave default)

### CHANGELOG.md Format

Create a `CHANGELOG.md` file in the root directory:

```markdown
# SOFL Changelog

## [v0.18.0] - 2024-01-XX

### New Features

- Feature description

### Bug Fixes

- Bug fix description

### Other Changes

- Other change description
```

The workflow will automatically extract the latest version section.

### Git Commits

The workflow analyzes commit messages and categorizes them:

- **New Features**: Commits starting with `feat:`, `add:`, `new:`
- **Bug Fixes**: Commits starting with `fix:`, `bug:`
- **Other Changes**: All other commits

### Auto Mode

When set to "auto":

1. If `CHANGELOG.md` exists → use changelog
2. Otherwise → generate from git commits

## Examples

### Example 1: Manual Release

```yaml
# Workflow inputs
version: "0.18.0"
release_body: |
  ## What's New

  This release includes major improvements to the CI/CD pipeline.

  ### Key Features
  - Flexible release body generation
  - Enhanced package building
release_body_source: "auto"
```

### Example 2: Using CHANGELOG.md

```yaml
# Workflow inputs
version: "" # Auto-detect from meson.build
release_body: "" # Leave empty to use CHANGELOG.md
release_body_source: "changelog"
```

### Example 3: Git Commits

```yaml
# Workflow inputs
version: "0.18.0"
release_body: "" # Leave empty for auto-generation
release_body_source: "git_commits"
```

## Git Commit Message Guidelines

For best results with git commit generation:

```bash
# Features
git commit -m "feat: add new game launcher support"

# Bug fixes
git commit -m "fix: resolve crash on startup"

# Documentation
git commit -m "docs: update installation guide"

# Refactoring
git commit -m "refactor: improve code structure"
```

## Workflow Structure

The workflow consists of:

1. **get-version** - Extracts version from meson.build or user input
2. **generate-release-body** - Creates release body based on selected method
3. **build-\* jobs** - Build packages for different distributions
4. **release** - Creates GitHub release with generated body

## Files

- `.github/workflows/build-packages.yml` - Main workflow
- `CHANGELOG.md` - Optional changelog file
- `docs/RELEASE_WORKFLOW.md` - This documentation
