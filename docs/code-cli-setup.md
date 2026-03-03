# Install the `code` command on macOS

Add the `code` executable to your `PATH` to open files directly from the
terminal in Visual Studio Code.

1. Launch Visual Studio Code.
2. Open the Command Palette (`Cmd+Shift+P`).
3. Type `Shell Command`.
4. Select **Shell Command: Install 'code' command in PATH**.
5. Reopen your terminal to refresh `PATH`.
6. Verify with `code -v`.

You can now run `code ~/.docker/config.json` to open any file in VS Code
from the terminal.
