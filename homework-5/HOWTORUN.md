# How to Run

This covers all four MCP servers registered in [`.mcp.json`](.mcp.json): GitHub, Filesystem, Notion, and the custom FastMCP `lorem-ipsum` server.

## Prerequisites

- [Claude Code](https://claude.ai/code) CLI installed and signed in.
- Node.js + `npx` available on PATH (used to fetch the official GitHub/Filesystem/Notion MCP servers on demand).
- Python 3.11+ available (used by the custom server's local virtual environment).

## 1. GitHub MCP

1. Create a GitHub Personal Access Token (Settings → Developer settings → Fine-grained tokens) scoped to `PeterMoroz17/gen-ai-software-engineering` with `Contents: Read-only` and `Pull requests: Read-only` (add `Issues: Read & write` if you want to demo issue creation).
2. Set it as an environment variable before launching Claude Code (do **not** commit the token):
   ```powershell
   $env:GITHUB_PERSONAL_ACCESS_TOKEN = "ghp_xxxxxxxxxxxx"
   ```
3. Launch Claude Code from `homework-5/` so it picks up `.mcp.json`. Run `/mcp` to confirm the `github` server is connected.
4. Example prompt: *"List the last 5 pull requests on PeterMoroz17/gen-ai-software-engineering."*
5. Screenshot saved to `docs/screenshots/github-mcp-result.png`.

## 2. Filesystem MCP

1. No credentials needed — `.mcp.json` already points the `filesystem` server at `.` (the `homework-5/` directory).
2. Run `/mcp` to confirm the `filesystem` server is connected.
3. Example prompt: *"List the files in the current directory"* or *"Read README.md and summarize it."*
4. Screenshot saved to `docs/screenshots/filesystem-mcp-result.png`.

## 3. Notion MCP

1. Create a Notion internal integration at [notion.so/my-integrations](https://www.notion.so/my-integrations) and copy its secret.
2. Share the page/database that tracks bugs with that integration (open the page → `•••` → Connections → add your integration).
3. Set the token as an environment variable:
   ```powershell
   $env:NOTION_TOKEN = "ntn_xxxxxxxxxxxx"
   ```
4. Run `/mcp` to confirm the `notion` server is connected.
5. Prompt used: *"Give me the tickets/pages of the last 5 bugs on a project"* (against a real Notion project).
6. Screenshot of request + response saved to `docs/screenshots/jira-or-notion-mcp-result.png` (only page IDs/titles, no sensitive content).

## 4. Custom MCP server (`custom-mcp-server/`)

### Install dependencies

A local virtual environment is already set up at `custom-mcp-server/.venv` (not committed). To recreate it from scratch:

```powershell
cd custom-mcp-server
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.txt` includes `fastmcp`.

### Run the server standalone (sanity check)

```powershell
cd custom-mcp-server
.\.venv\Scripts\python.exe server.py
```

This starts the FastMCP server over stdio. It will appear to "hang" — that's expected, it's waiting for an MCP client to connect. Press `Ctrl+C` to stop.

### Connect via MCP configuration

`.mcp.json` (at the `homework-5/` root) already registers it:

```json
"lorem-ipsum": {
  "command": "custom-mcp-server/.venv/Scripts/python.exe",
  "args": ["custom-mcp-server/server.py"]
}
```

Launch Claude Code from `homework-5/` and run `/mcp` to confirm the `lorem-ipsum` server is connected with no errors.

### Use/test the `read` tool

In Claude Code, ask:

- *"Use the read tool from the lorem-ipsum server to get 30 words."*
- *"Use the read tool with word_count=10."*

Expected behavior: the tool returns exactly that many words from `lorem-ipsum.md` (default `30` if `word_count` is omitted). The same content is also available as a resource at `lorem://text` (default 30 words) and `lorem://text/{word_count}` (custom count).

Screenshot of a successful `read` tool call saved to `docs/screenshots/custom-mcp-read-tool-result.png`.

## Verification checklist

- [x] Starting command for the custom server works (`server.py` runs under the venv's Python without import errors).
- [x] `.mcp.json` is valid JSON and points the `lorem-ipsum` entry at the venv interpreter and `server.py`.
- [x] `fastmcp` is explicitly listed in `custom-mcp-server/requirements.txt`.
- [ ] All four servers show as connected via `/mcp` in Claude Code (verify locally with your own credentials).
- [ ] Screenshots for all four interactions captured in `docs/screenshots/`.
