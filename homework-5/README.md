# Homework 5: Configure MCP Servers

**Author:** Peter Moroz

## Overview

This homework configures four MCP (Model Context Protocol) servers for use with Claude Code:

1. **GitHub MCP** — official server, connected to [`PeterMoroz17/gen-ai-software-engineering`](https://github.com/PeterMoroz17/gen-ai-software-engineering).
2. **Filesystem MCP** — official server, exposing the `homework-5/` directory.
3. **Notion MCP** — official server, used to query the last 5 bug pages on a Notion project.
4. **Custom MCP server** (`custom-mcp-server/`) — built from scratch with [FastMCP](https://gofastmcp.com), exposing a lorem-ipsum text resource and a `read` tool.

All four servers are registered in [`.mcp.json`](.mcp.json) at the root of this folder.

## Resources vs. Tools (custom server)

- **Resource** — a URI Claude can *read* from, like a file or an API endpoint. Reading a resource has no side effects; it just returns content. Our custom server exposes `lorem://text` and `lorem://text/{word_count}`, which read from `lorem-ipsum.md` and return the first N words.
- **Tool** — an *action* Claude can *call*, with arguments, to perform an operation. Our custom server exposes a `read` tool that takes an optional `word_count` parameter (default `30`) and returns the same word-limited content as the resource.

See [HOWTORUN.md](HOWTORUN.md) for installation, running, and usage instructions, and `docs/screenshots/` for proof of each working interaction.

## AI Tools Used

Claude Code (CLI 2.1.141) was used throughout — for planning, scaffolding the
custom server, writing documentation, debugging the Notion env var mismatch,
and verifying the final deliverables.  
See the PR description for the full
session breakdown with screenshots.