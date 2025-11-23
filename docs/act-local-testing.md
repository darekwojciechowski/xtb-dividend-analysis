# Running `act` Locally

This note covers the minimum setup required to run the GitHub Actions workflow locally with [`act`](https://github.com/nektos/act) on macOS.

## Prerequisites

1. **Docker Desktop running** – start Docker Desktop (`open -a Docker`). `act` uses Docker containers for every job, so the daemon must stay online.
2. **Fix Docker credential helper** – if `act` fails with `error getting credentials - err: exit status 1`, edit `~/.docker/config.json` and remove the line:
   ```json
   "credsStore": "desktop",
   ```
   Save the file and rerun `docker pull hello-world` to verify the CLI works without prompting for credentials. You can restore the entry later if needed.
3. **Install the VS Code CLI (optional but handy)** – follow `docs/code-cli-setup.md` if you want to open files via `code ~/.docker/config.json`.

## Installing act

```bash
brew install act
```

## Recommended invocation

```bash
act push -j test \
  --container-architecture linux/amd64 \
  -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

Explanation:
- `--container-architecture linux/amd64` – required on Apple Silicon so Docker pulls the correct image.
- `-P ubuntu-latest=...` – tells `act` which image to use for GitHub's `ubuntu-latest` runners.
- Add more `-P` mappings if you want to emulate Windows or macOS jobs (or remove those OS entries from the workflow while testing locally).

## Handling workflow steps that need GitHub tokens

Some steps (e.g., artifact upload, test reporter) expect `GITHUB_TOKEN`/`ACTIONS_RUNTIME_TOKEN`. When running locally, either:
- Provide a personal access token via a secrets file: `act ... --secret-file .secrets` with `GH_TOKEN=...`, or
- Guard those steps in the workflow with `if: ${{ !env.ACT }}` so they skip during local dry runs.

With these adjustments, the `act` execution can progress through the relevant jobs without the Docker credential errors or missing-token failures.
