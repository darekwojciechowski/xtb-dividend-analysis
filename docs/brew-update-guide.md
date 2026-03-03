# Homebrew update guide

Keep Homebrew and its packages up to date on macOS.

## Update Homebrew

Fetch the latest package index and metadata:

```bash
brew update
```

## Upgrade all outdated packages

Install newer versions of every outdated formula:

```bash
brew upgrade
```

To upgrade a specific formula only (for example, Python 3.14):

```bash
brew upgrade python@3.14
```

## Clean up old versions

Remove cached downloads and outdated package versions to free disk space:

```bash
brew cleanup
```

## Verify installed versions

Check which version of a formula is active:

```bash
brew info python@3.14
python3 --version
```

## Next steps

- After upgrading Python, recreate any affected Poetry virtual environments:
  `poetry env remove --all && poetry install`
- After upgrading Poetry itself (`poetry` appears in the outdated list), verify
  it still resolves correctly: `poetry --version`
