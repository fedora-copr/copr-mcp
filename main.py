import argparse
import logging
from munch import Munch
from typing import Callable, Literal, Annotated
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from mcp.server.fastmcp import FastMCP
from copr.v3 import Client
import copr_models


class Project(copr_models.Project):
    web_url: str


class BuildStatus(BaseModel):
    id: int
    state: str
    name: str | None = None


class Build(copr_models.Build):
    web_url: str


class BuildFromDistGit(BaseModel):
    """
    Use this schema when you want to build a package Fedora or any other
    DistGit instance
    """
    source_type: Literal["distgit"] = "distgit"
    packagename: str
    namespace: str | None = None


class BuildFromPyPI(BaseModel):
    """
    Use this schema when you want to build a package from PyPI
    """
    source_type: Literal["pypi"] = "pypi"
    packagename: str
    spec_template: str | None = None


# We need to annotate this with a discriminator otherwise AI sometimes doesn't
# know what type to use and therefore uses the first one.
# class to use
BuildSource = Annotated[
    BuildFromDistGit | BuildFromPyPI,
    Field(discriminator="source_type"),
]


logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def web_url(client: Client, data: Munch) -> str:
    """
    This should be either part of python-copr or returned by the API
    """
    match data.__proxy__.__class__.__name__:
        case "ProjectProxy":
            project = data
            # Taken from copr-cli action_create
            owner_part = project.ownername.replace("@", "g/")
            return "/".join([
                client.config["copr_url"].strip("/"),
                "coprs", owner_part, project.name, "",
            ])
        case "BuildProxy":
            build = data
            return "/".join([
                client.config["copr_url"].strip("/"),
                "coprs/build",
                str(build.id),
            ])
    raise ValueError("Don't know the web URL for this input data")


def copr_get_project(
    ownername: str,
    projectname: str,
) -> Project:
    """
    Get information about Copr project with a given ownername/projectname
    """
    log.debug("copr_get_project: %s/%s", ownername, projectname)
    client = Client.create_from_config_file()
    project = client.project_proxy.get(ownername, projectname)
    project.web_url = web_url(client, project)
    return Project.model_validate(project)


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
    log.debug("copr_create_project: %s/%s", ownername, projectname)
    client = Client.create_from_config_file()
    project = client.project_proxy.add(ownername, projectname, chroots)
    project.web_url = web_url(client, project)
    return Project.model_validate(project)


def copr_build_status(build_id: int) -> BuildStatus:
    """
    Get the status of a Copr build by its ID.
    """
    log.debug("copr_build_status: %s", build_id)
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
    log.debug("copr_list_builds: %s/%s", ownername, projectname)
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
    log.debug(
        "copr_submit_build: %s/%s %s",
        ownername, projectname, source.__class__.__name__,
    )
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

    build.web_url = web_url(client, build)
    return Build.model_validate(build)


def copr_enable_repository(ownername: str, projectname: str) -> str:
    """
    Provide instructions for enabling a Copr repository on the user system.
    This requires root privileges and must be run manually by the user.
    """
    return (
        f"This action requires root privileges and therefore requires a manual"
        f"step from the user.\n"
        f"To enable this Copr repository run the following command:\n\n"
        f"    sudo dnf copr enable {ownername}/{projectname}"
    )


def copr_list_mock_chroots() -> list[str]:
    """
    Get a list of all mock chroots that you can create or use in copr. The
    response copr will give may vary over time, i.e. when a new Fedora or RHEL
    version is released.
    """
    log.debug("copr_list_mock_chroots")
    client = Client.create_from_config_file()
    return list(client.mock_chroot_proxy.get_list().keys())


def copr_list_mock_chroots_for_project(ownername: str, projectname:str) -> list[str] | None: 
    """
    Get a list of all mock chroots that are configured for a given copr project
    or nothing if the project could not be found. The response may vary over
    time, depending on if chroots where added or removed from the copr project.
    """
    log.debug("copr_list_mock_chroots_for_project: %s/%s", ownername, projectname)
    client = Client.create_from_config_file()
    project = client.project_proxy.get(ownername=ownername, projectname=projectname)
    if project is None or 'chroot_repos' not in project:
        return None
    return list(project['chroot_repos'].keys())


def run_mcp(tools: list[Callable], args):
    mcp = FastMCP("copr")
    for tool in tools:
        mcp.add_tool(tool)
    mcp.run()


def run_prompt(tools: list[Callable], args):
    instructions = (
        "You help manage Copr builds. Use tools to get real information.",
    )
    agent = Agent(
        "anthropic:claude-opus-4-6",
        instructions=instructions,
    )
    for tool in tools:
        agent.tool_plain(tool)
    result = agent.run_sync(args.prompt)
    print(result.output)


def main():
    parser = argparse.ArgumentParser(description="Copr AI assistant")
    parser.add_argument(
        "--prompt",
        help="Don't run MCP and send a prompt directly",
    )
    args = parser.parse_args()
    client = Client.create_from_config_file()
    tools = [
        copr_build_status,
        copr_list_builds,
        copr_get_project,
        copr_create_project,
        copr_submit_build,
        copr_enable_repository,
        copr_list_mock_chroots,
        copr_list_mock_chroots_for_project,
        # We probably don't have to implement wrappers around every python-copr
        # function. We can simply register the client methods like this.
        client.base_proxy.auth_check,
    ]
    if args.prompt:
        run_prompt(tools, args)
    else:
        run_mcp(tools, args)


if __name__ == "__main__":
    main()
