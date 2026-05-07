# Independent Workspace Launcher

Each workspace runs with its own:

- account database
- customer and mail data
- uploaded files
- downloads folder
- Chrome profile
- config.ini
- service logs
- port

When a workspace is created for the first time, the launcher copies the current root `config.ini` into that workspace. Existing API settings, including `ai.base_url`, `ai.model`, `ai.api_key`, mail username, mail password/auth code, SMTP/IMAP hosts, templates, and runtime settings are preserved inside that workspace.

## Start

Double click:

```bat
run_workspace.bat
```

Then enter a workspace name and port, for example:

```text
user1 / 5001
user2 / 5002
```

You can also start directly:

```bat
run_workspace.bat user1 5001
run_workspace.bat user2 5002
```

The workspace files are created under:

```text
workspaces\user1\
workspaces\user2\
```

Each workspace has its own config file:

```text
workspaces\user1\config.ini
workspaces\user2\config.ini
```

After a workspace has been created, editing one workspace config will not affect the others.

## Stop

```bat
stop_workspace.bat user1 5001
```

## Notes

Use a different port for each workspace. The first login account in every workspace is independent, with the default administrator:

```text
admin / admin123
```
