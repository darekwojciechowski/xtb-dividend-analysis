# Run `act` locally

Run GitHub Actions workflows locally with [`act`](https://github.com/nektos/act)
on macOS.

## Prerequisites

1. **Start Docker Desktop** (`open -a Docker`). `act` uses Docker containers for
   every job, so the daemon must stay online.
2. **Fix the Docker credential helper** if `act` fails with
   `error getting credentials - err: exit status 1`. Edit
   `~/.docker/config.json` and remove:
   ```json
   "credsStore": "desktop",
   ```
   Verify with `docker pull hello-world`. You can restore the entry later.
3. **Optional:** Install the VS Code CLI — see [docs/code-cli-setup.md](code-cli-setup.md).

## Install act

```bash
brew install act
```

## Run

```bash
act push -j test \
  --container-architecture linux/amd64 \
  -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

- `--container-architecture linux/amd64` — required on Apple Silicon.
- `-P ubuntu-latest=...` — specifies the image for `ubuntu-latest` runners.

## GitHub tokens

Steps such as artifact upload and test reporter expect `GITHUB_TOKEN` or
`ACTIONS_RUNTIME_TOKEN`. To handle this locally:

- Pass a personal access token via `act ... --secret-file .secrets` with
  `GH_TOKEN=<token>`, or
- Skip those steps in the workflow with `if: ${{ !env.ACT }}`.

## Clean up

`act` removes temporary containers automatically but leaves images and caches
on disk:

- `docker system prune -f` — removes unused images and layers.
- `rm -rf ~/.cache/act` — clears cached actions.
- `git clean -fd` — removes generated artifacts such as `coverage.xml`.
