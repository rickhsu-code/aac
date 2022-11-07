# -*- coding: utf-8 -*-

# Copyright: (c) 2022, Daniel Schmidt <danischm@cisco.com>

# Expects the following environment variables:
# - WEBEX_TOKEN
# - WEBEX_ROOM_ID
# - JOB_NAME
# - BUILD_DISPLAY_NAME
# - RUN_DISPLAY_URL
# - BUILD_URL
# - GIT_COMMIT_MESSAGE
# - GIT_URL
# - GIT_COMMIT_AUTHOR
# - GIT_BRANCH
# - GIT_EVENT
# - BUILD_STATUS
# - NAE_HOST
# - CONFIG_REPO_OWNER
# - CONFIG_REPO_NAME

import json
import os
import re
import requests

TEMPLATE = """[**[{status}] {job_name} {build}**]({url})
* _Commit_: [{commit}]({git_url})
* _Author_: {author}
* _Branch_: {branch}
* _Event_: {event}
""".format(
    status=str(os.getenv("BUILD_STATUS") or "").lower(),
    job_name=str(os.getenv("JOB_NAME")).rsplit("/", 1)[0],
    build=os.getenv("BUILD_DISPLAY_NAME"),
    url=os.getenv("RUN_DISPLAY_URL"),
    commit=os.getenv("GIT_COMMIT_MESSAGE"),
    git_url=os.getenv("GIT_URL"),
    author=os.getenv("GIT_COMMIT_AUTHOR"),
    branch=os.getenv("GIT_BRANCH"),
    event=os.getenv("GIT_EVENT"),
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

TEST_OUTPUT = """\n**Test Summary** [**APIC**]({url}artifact/test_results/lab/apic1/log.html) [**MSO**]({url}artifact/test_results/lab/mso1/log.html)
```
""".format(
    url=os.getenv("BUILD_URL"),
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
