import argparse
import json
import logging
import subprocess

from pydantic import BaseModel
from pydantic_ai import Agent
from mcp.server.fastmcp import FastMCP


class BuildStatus(BaseModel):
    id: int
    state: str
    name: str | None = None


logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def copr_build_status(build_id: int) -> BuildStatus:
    """
    Get the status of a Copr build by its ID.
    """
    cmd = ["copr-cli", "status", str(build_id)]
    result = subprocess.run(cmd, capture_output=True, text=True)

    log.debug("Running: %s", cmd)
    log.debug("stdout: %s", result.stdout)
    log.debug("stderr: %s", result.stderr)

    if result.returncode != 0:
        raise ValueError(result.stderr.strip())

    return BuildStatus(
        id=build_id,
        state=result.stdout.strip(),
    )


def copr_list_builds(ownername: str, projectname: str) -> list[BuildStatus]:
    """
    Get the status of all builds in a Copr project identified by its
    ownername/projectname.
    """
    fullname = f"{ownername}/{projectname}"
    cmd = [
        "copr-cli", "list-builds",
        "--output-format", "json",
        fullname,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    log.debug("Running: %s", cmd)
    log.debug("stdout: %s", result.stdout)
    log.debug("stderr: %s", result.stderr)

    if result.returncode != 0:
        raise ValueError(result.stderr.strip())

    try:
        data = json.loads(result.stdout.strip())
    except json.JSONDecodeError as ex:
        raise RuntimeError(f"Failed to parse JSON: {result.stdout!r}") from ex

    return [
        BuildStatus(
            id=build["id"],
            state=build["state"],
            name=build["name"],
        )
        for build in data
    ]


def run_mcp(args):
    mcp = FastMCP("copr-ai")
    mcp.add_tool(copr_build_status)
    mcp.add_tool(copr_list_builds)
    mcp.run()


def run_prompt(args):
    instructions = (
        "You help manage Copr builds. Use tools to get real information.",
    )
    agent = Agent(
        "anthropic:claude-opus-4-6",
        instructions=instructions,
    )
    agent.tool_plain(copr_build_status)
    agent.tool_plain(copr_list_builds)

    result = agent.run_sync(args.prompt)
    print(result.output)


def main():
    parser = argparse.ArgumentParser(description="Copr AI assistant")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--mcp",
        action="store_true",
        help="Run as MCP server",
    )
    group.add_argument(
        "--prompt",
        help="Run as interactive CLI",
    )
    args = parser.parse_args()

    if args.prompt:
        run_prompt(args)
    else:
        run_mcp(args)


if __name__ == "__main__":
    main()
