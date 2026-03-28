import argparse
import logging
from pydantic import BaseModel
from pydantic_ai import Agent
from mcp.server.fastmcp import FastMCP
from copr.v3 import Client


class Project(BaseModel):
    id: int
    web_url: str
    ownername: str
    name: str
    full_name: str


class BuildStatus(BaseModel):
    id: int
    state: str
    name: str | None = None


class Build(BaseModel):
    id: int
    web_url: str
    state: str
    submitter: str


class BuildFromDistGit(BaseModel):
    packagename: str
    namespace: str | None = None


class BuildFromPyPI(BaseModel):
    packagename: str
    spec_template: str | None = None


BuildSource = BuildFromDistGit | BuildFromPyPI


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
        web_url=web_url,
        ownername=project.ownername,
        name=project.name,
        full_name=project.full_name,
    )


def copr_build_status(build_id: int) -> BuildStatus:
    """
    Get the status of a Copr build by its ID.
    """
    client = Client.create_from_config_file()
    build = client.build_proxy.get(build_id)
    return BuildStatus(
        id=build.id,
        state=build.state,
    )


def copr_list_builds(ownername: str, projectname: str) -> list[BuildStatus]:
    """
    Get the status of all builds in a Copr project identified by its
    ownername/projectname.
    """
    client = Client.create_from_config_file()
    builds = client.build_proxy.get_list(ownername, projectname)
    return [
        BuildStatus(
            id=build.id,
            state=build.state,
            name=build.source_package["name"],
        )
        for build in builds
    ]


def copr_submit_build(
    ownername: str,
    projectname: str,
    source: BuildSource,
) -> Build:
    """
    Submit a new build into a Copr project defined by its ownername and
    projectname. Copr supports multiple source types, see the documentation
    https://docs.copr.fedorainfracloud.org/user_documentation.html#build-source-types
    """
    client = Client.create_from_config_file()
    match source:
        case BuildFromDistGit():
            build = client.build_proxy.create_from_distgit(
                ownername,
                projectname,
                source.packagename,
                namespace=source.namespace,

            )
        case BuildFromPyPI():
            build = client.build_proxy.create_from_pypi(
                ownername,
                projectname,
                source.packagename,
                spec_template=source.spec_template,
            )

    web_url = "/".join([
        client.config["copr_url"].strip("/"),
        "coprs/build",
        str(build.id),
    ])

    return Build(
        id=build.id,
        web_url=web_url,
        state=build.state,
        submitter=build.submitter,
    )


def run_mcp(args):
    mcp = FastMCP("copr-ai")
    mcp.add_tool(copr_build_status)
    mcp.add_tool(copr_list_builds)
    mcp.add_tool(copr_create_project)
    mcp.add_tool(copr_submit_build)
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
    agent.tool_plain(copr_submit_build)

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
