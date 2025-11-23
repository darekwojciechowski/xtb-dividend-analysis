# Installing the `code` Command on macOS

Use this procedure to add the `code` executable to your `PATH`, so you can open files (for example `~/.docker/config.json`) straight from the terminal in Visual Studio Code.

1. Launch Visual Studio Code from the Dock or Launchpad.
2. Choose `View → Command Palette…` (`Cmd+Shift+P`).
3. Type `Shell Command`.
4. Select `Shell Command: Install 'code' command in PATH`.
5. Close and reopen your terminal session to refresh `PATH`.
6. Verify the installation with `code -v`.

After these steps you can run commands like `code ~/.docker/config.json` to edit files in VS Code instead of a terminal editor.
