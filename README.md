# Copr AI

## Prerequisites

Install dependencies

```
uv sync
```

## Interactive Usage

Go to <https://console.anthropic.com>, "API Keys" and generate a new key. Then
export it in your terminal:

```
export ANTHROPIC_API_KEY=...
```

Then run

```
uv run main.py --prompt "Tell me the status of Copr build 8101723"
```

## MCP Usage

Register the MCP server

```
claude mcp add copr-ai \
    -- uv run --directory /home/jkadlcik/git/copr-ai python main.py --mcp
```

Then create a new claude session and ask it questions like

> Tell me the status of Copr build 8101723
> Can you give me last 5 builds from the frostyx/foo Copr project?

If you don't need this MCP server anymore, uninstall it.

```
claude mcp remove copr-ai
```
