# Chapter 09 — MCP (Model Context Protocol)

This chapter covers hands-on learning of MCP — setting up, configuring, and using MCP servers with VS Code and Command Code.

## What is MCP?

MCP (Model Context Protocol) is a universal standard that allows AI assistants to connect with external tools and data sources. Think of it as **USB-C for AI** — one protocol to connect browsers, project management tools, databases, and more.

## MCP Servers Configured

### 1. Playwright MCP (Browser Automation)

The Playwright MCP server lets AI drive a real browser — navigate pages, click elements, fill forms, take screenshots, and extract page content.

**Config** (`.vscode/mcp.json`):
```json
"playwright": {
    "command": "npx",
    "args": ["-y", "@playwright/mcp@latest"],
    "type": "stdio"
}
```

**Tools available**:
- `browser_navigate` — Navigate to a URL
- `browser_snapshot` — Get accessible page snapshot with interactive elements
- `browser_click` — Click on an element
- `browser_fill` — Fill a form field
- `browser_close` — Close the browser

### 2. Atlassian JIRA MCP (Issue Tracking)

The Atlassian MCP server connects AI to JIRA Cloud for fetching, searching, and managing issues.

**Config** (`.vscode/mcp.json`):
```json
"com.atlassian/atlassian-mcp-server": {
    "type": "http",
    "url": "https://mcp.atlassian.com/v1/mcp"
}
```

This is a cloud-hosted HTTP MCP server — no `npm install` needed. Authentication happens via Atlassian account.

## Commands Reference

### Setting up MCP servers in VS Code/Command Code

```bash
# Add Playwright MCP (stdio transport)
cmdc mcp add playwright -- npx -y @playwright/mcp

# Add Atlassian MCP (HTTP transport)
cmdc mcp add --transport http jira https://mcp.atlassian.com/v1/mcp

# List configured servers
cmdc mcp list

# Get server details
cmdc mcp get <server-name>
```

### Viewing Available Tools

- **VS Code**: Click the gear icon on the chat panel → MCP servers list → click a server to see its tools
- **MCP Inspector** (for debugging): `npx @modelcontextprotocol/inspector -p <port> npx -y @playwright/mcp`

## Key Learnings

1. **MCP Server Types**:
   - **stdio** — Server runs as a local process (e.g., `npx @playwright/mcp`)
   - **http** — Server is a cloud-hosted API (e.g., `https://mcp.atlassian.com/v1/mcp`)

2. **Config Scopes** (Command Code):
   - **User** (`~/.commandcode/mcp.json`) — Available across all projects
   - **Project** (`<project>/.mcp.json`) — Checked into git, shared with team
   - **Local** (`~/.commandcode/projects/<slug>/mcp.json`) — Private to this machine

3. **VS Code config** lives in `.vscode/mcp.json` — workspace-specific, uses `"servers"` key (different format from Command Code's `"mcpServers"`)

4. **Playwright MCP vs. agent-browser**: Playwright MCP provides tools through the MCP protocol; `agent-browser` is a separate Rust-based CLI that does browser automation via shell commands.

5. **JIRA via HTTP MCP**: The Atlassian MCP server is a cloud service at `mcp.atlassian.com` — no local package needed. Just configure the URL and authenticate.

## Screenshots

| File | Description |
|---|---|
| `PW_MCP_01.png` | Playwright MCP debug view showing available browser tools |
| `PW_MCP_02.png` | Playwright MCP successfully opening gmail.com |
| `JIRA_MCP_01.png` | JIRA MCP fetching SCRUM-12 story |
