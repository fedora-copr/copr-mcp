import json
import logging
import subprocess

from pydantic import BaseModel
from pydantic_ai import Agent


class BuildStatus(BaseModel):
    id: int
    state: str
    name: str | None = None


logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


agent = Agent(
    "anthropic:claude-opus-4-6",
    instructions="You help manage Copr builds. Use tools to get real information.",
)


@agent.tool_plain
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


@agent.tool_plain
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


def main():
    prompt = input("Ask about your Copr builds: ")
    result = agent.run_sync(prompt)
    print(result.output)


if __name__ == "__main__":
    main()
