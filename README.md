# Copr MCP

## Prerequisites

Install dependencies

```
uv sync
```


## MCP Usage

Register the MCP server

```
claude mcp add copr --scope user \
    -- uv run --directory `pwd` python main.py
```

Then create a new claude session and ask it questions like

> Tell me the status of Copr build 8101723

> Can you give me last 5 builds from the frostyx/foo Copr project?

> Build the DistGit package hello in my frostyx/foo project

> Create a Copr project frostyx/foo with a fedora-43-x86_64 chroot

If you don't need this MCP server anymore, uninstall it.

```
claude mcp remove copr
```


## Development

Go to <https://console.anthropic.com>, "API Keys" and generate a new key. Then
export it in your terminal:

```
export ANTHROPIC_API_KEY=...
```

Then run

```
uv run main.py --prompt "Tell me the status of Copr build 8101723"
```

## Tests

```
uv run mypy .
uv run ruff check
uv run pytest
```
