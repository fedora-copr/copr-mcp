import argparse
import json
import logging
import subprocess

from pydantic import BaseModel
from pydantic_ai import Agent
from mcp.server.fastmcp import FastMCP
from copr.v3 import Client


class Project(BaseModel):
    id: int
    ownername: str
    name: str
    full_name: str
    web_url: str


class BuildStatus(BaseModel):
    id: int
    state: str
    name: str | None = None


logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def copr_create_project(
    ownername: str,
    projectname: str,
    chroots: list[str],
) -> Project:
    """
    Create a Copr project with a given name for a specified owner.
    When creating a new project, at least one chroot must be specified. For
    example `fedora-rawhide-x86_64`
    """
    client = Client.create_from_config_file()
    project = client.project_proxy.add(ownername, projectname, chroots)

    # Taken from copr-cli action_create
    # This should be either part of python-copr or returned by the API
    owner_part = project.ownername.replace("@", "g/")
    web_url = "/".join([
        client.config["copr_url"].strip("/"),
        "coprs", owner_part, project.name, "",
    ])

    return Project(
        id=project.id,
        ownername=project.ownername,
        name=project.name,
        full_name=project.full_name,
        web_url=web_url,
    )


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
    mcp.add_tool(copr_create_project)
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
    agent.tool_plain(copr_create_project)

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
