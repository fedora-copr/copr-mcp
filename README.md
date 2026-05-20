# Copr MCP

# Demo

Please see the [First look at the Copr MCP server](https://www.youtube.com/watch?v=3gYktJT-Cr0).

[![Demo](https://i1.ytimg.com/vi/3gYktJT-Cr0/maxresdefault.jpg)](https://www.youtube.com/watch?v=3gYktJT-Cr0)



## Prerequisites

Install dependencies

```console
uv sync
```


## MCP Usage

Register the MCP server with Claude Code, Codex, Cursor, or any other agent.

### Claude Code

To register the `copr` server with Claude Code, execute this command

```console
$ claude mcp add copr --scope user \
    -- uv run --directory "$(pwd)" python main.py
```

If you don't need this MCP server anymore, uninstall it.

```console
$ claude mcp remove copr
```

### Codex

```console
$ codex mcp add copr -- uv run --directory "$(pwd)" python main.py
```

If you don't need this MCP server anymore, uninstall it.

```console
$ codex mcp remove copr
```

### Cursor 

If you use Cursor, open or create `~/.cursor/mcp.json` and add the `copr`
entry to the list of `mcpServers`.

Change the directory (`~/src/copr-mcp`) to wherever you've cloned this
`copr-mcp` project.

```yaml
{
  "mcpServers": {
    "copr": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "~/src/copr-mcp",
        "python",
        "main.py"
      ]
    }
  }
}
```

If you don't need this MCP server anymore, removing the `copr`
entry from the `mcpServers` list in `~/.cursor/mcp.json`.


### Run tools

Once the MCP server is registered, go to i.e. Claude or Cursor and ask it
questions like

> Tell me the status of Copr build 8101723

> Can you give me last 5 builds from the frostyx/foo Copr project?

> Build the DistGit package hello in my frostyx/foo project

> Create a Copr project frostyx/foo with a fedora-43-x86_64 chroot


## Development

Go to <https://console.anthropic.com>, "API Keys" and generate a new key. Then
export it in your terminal:

```console
$ export ANTHROPIC_API_KEY=...
```

Then run

```console
$ uv run main.py --prompt "Tell me the status of Copr build 8101723"
```

To use a different model pass `--model`

```console
$ uv run main.py --model gpt-5-mini --prompt "Tell me the status of Copr build 8101723"
```

Full list of models can be found here: https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.KnownModelName

## Tests

```console
$ uv run mypy .
$ uv run ruff check
$ uv run pytest
```
