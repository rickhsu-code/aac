# -*- coding: utf-8 -*-

# Copyright: (c) 2022, Daniel Schmidt <danischm@cisco.com>

# Expects the following environment variables:
# - WEBEX_TOKEN
# - WEBEX_ROOM_ID
# - DRONE_BUILD_STATUS
# - DRONE_REPO_OWNER
# - DRONE_REPO_NAME
# - DRONE_BUILD_NUMBER
# - DRONE_BUILD_LINK
# - DRONE_COMMIT_MESSAGE
# - DRONE_COMMIT_LINK
# - DRONE_COMMIT_AUTHOR_NAME
# - DRONE_COMMIT_AUTHOR_EMAIL
# - DRONE_COMMIT_BRANCH
# - DRONE_BUILD_EVENT
# - CONFIG_REPO_OWNER
# - CONFIG_REPO_NAME
# - NAE_HOST

import json
import os
import re
import requests

TEMPLATE = """[**[{build_status}] {repo_owner}/{repo_name} #{build_number}**]({build_link})
* _Commit_: [{commit_message}]({commit_link})
* _Author_: {commit_author_name} {commit_author_email}
* _Branch_: {commit_branch}
* _Event_:  {build_event}
""".format(
    build_status=os.getenv("DRONE_BUILD_STATUS"),
    repo_owner=os.getenv("DRONE_REPO_OWNER"),
    repo_name=os.getenv("DRONE_REPO_NAME"),
    build_number=os.getenv("DRONE_BUILD_NUMBER"),
    build_link=os.getenv("DRONE_BUILD_LINK"),
    commit_message=os.getenv("DRONE_COMMIT_MESSAGE"),
    commit_link=os.getenv("DRONE_COMMIT_LINK"),
    commit_author_name=os.getenv("DRONE_COMMIT_AUTHOR_NAME"),
    commit_author_email=os.getenv("DRONE_COMMIT_AUTHOR_EMAIL"),
    commit_branch=os.getenv("DRONE_COMMIT_BRANCH"),
    build_event=os.getenv("DRONE_BUILD_EVENT"),
)


VALIDATE_OUTPUT = """\n**Validation Errors**
```
"""

RENDER_OUTPUT = """\n**Render Summary**
```
"""

NAE_OUTPUT = """\n[**NAE Pre-Change Validation**](https://{})
```
""".format(
    os.getenv("NAE_HOST")
)

DEPLOY_OUTPUT = """\n[**Deploy Summary**](https://wwwin-github.cisco.com/{}/{}/commit/master)
```
""".format(
    os.getenv("CONFIG_REPO_OWNER"), os.getenv("CONFIG_REPO_NAME")
)

TEST_OUTPUT = """\n**Test Summary** [**APIC**](https://engci-maven-master.cisco.com/artifactory/list/AS-release/Community/{repo_owner}/{repo_name}/{build_number}/test_results/lab/apic1/log.html) [**MSO**](https://engci-maven-master.cisco.com/artifactory/list/AS-release/Community/{repo_owner}/{repo_name}/{build_number}/test_results/lab/mso1/log.html)
```
""".format(
    repo_owner=os.getenv("DRONE_REPO_OWNER"),
    repo_name=os.getenv("DRONE_REPO_NAME"),
    build_number=os.getenv("DRONE_BUILD_NUMBER"),
)


def parse_ansible_errors(filename):
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    lines = ""
    if os.path.isfile(filename):
        with open(filename, "r") as file:
            output = file.read()
            output = ansi_escape.sub("", output)
            add_lines = False
            for index, line in enumerate(output.split("\n")):
                if add_lines:
                    if len(line.strip()):
                        lines += line + "\n"
                    else:
                        add_lines = False
                if line.startswith("fatal:"):
                    lines += output.split("\n")[index - 1] + "\n"
                    lines += line + "\n"
                    add_lines = True
    return lines


def parse_ansible_summary(filename):
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    lines = ""
    if os.path.isfile(filename):
        with open(filename, "r") as file:
            output = file.read()
            output = ansi_escape.sub("", output)
            add_lines = False
            for index, line in enumerate(output.split("\n")):
                if add_lines:
                    if len(line.strip()):
                        lines += line + "\n"
                    else:
                        add_lines = False
                if line.startswith("PLAY RECAP"):
                    lines += line + "\n"
                    add_lines = True
    return lines


def main():
    message = TEMPLATE
    validate_lines = parse_ansible_errors("./validate_output.txt")
    if validate_lines:
        message += VALIDATE_OUTPUT + validate_lines + "\n```\n"
    render_lines = parse_ansible_summary("./render_output.txt")
    if render_lines:
        message += RENDER_OUTPUT + render_lines + "\n```\n"
    nae_lines = parse_ansible_errors("./nae_output.txt")
    if nae_lines:
        message += NAE_OUTPUT + nae_lines + "\n```\n"
    deploy_lines = parse_ansible_summary("./deploy_output.txt")
    if deploy_lines:
        message += DEPLOY_OUTPUT + deploy_lines + "\n```\n"
    test_lines = parse_ansible_summary("./test_output.txt")
    if test_lines:
        message += TEST_OUTPUT + test_lines + "\n```\n"

    body = {"roomId": os.getenv("WEBEX_ROOM_ID"), "markdown": message}
    headers = {
        "Authorization": "Bearer {}".format(os.getenv("WEBEX_TOKEN")),
        "Content-Type": "application/json",
    }
    resp = requests.post(
        "https://api.ciscospark.com/v1/messages", headers=headers, data=json.dumps(body)
    )
    if resp.status_code != 200:
        print(
            "Webex notification failed, status code: {}, response: {}.".format(
                resp.status_code, resp.text
            )
        )


if __name__ == "__main__":
    main()
