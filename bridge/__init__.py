from flask import Flask
from flask import request
from flask import redirect
from flask import abort

import requests

from .webgit import Gitea, Github
from .utils import issue_sentinel, generate_sentinel

app = Flask(__name__)
app.config.from_envvar('GIT_BRIDGE_SETTINGS')

@app.route("/bridge")
def index():
    return "you've reached the main page for an internal service. congrats!"

@app.route("/bridge/endpoints/gitea/repo", methods=["POST"])
def gitea_handle_repo_action():
    """
        Our plan of action for handling these events:
        - ignore deleting repositories -- this is a potentially destructive operation
          that *only* *the* *user* *should* *do*
        - create a cooresponding repo on github
        - create a push mirror to github so pushes to gitea get to github
        - create webhooks for issues (and in the future, pull requests) on both
          Gitea and Github ends
    """

    gitea = Gitea(app.config["GITEA_ACCESS_TOKEN"])
    github = Github(app.config["GITHUB_ACCESS_TOKEN"])

    data = request.json

    try:
        repository = data["repository"]

        repo_action = data["action"]
        repo_id = repository["id"]
        repo_owner = repository["owner"]["login"]
        repo_name = repository["name"]
        repo_description = repository["description"]

    except KeyError:
        abort(400) # the data isn't formatted correctly

    if not repo_action == "created":
        return ''

    github_created_repo_result = github.post(
        "https://api.github.com/user/repos",
        json={
            "name": repo_name,
            "description": repo_description,
            "homepage": "https://{}/{}/{}".format(
                app.config["GITEA_INSTANCE_DOMAIN"],
                repo_owner,
                repo_name,
            ),
        },
    )

    new_github_repo_url = github_created_repo_result.json()["html_url"]

    gitea_add_github_repo_url_result = gitea.patch(
        "https://{}/api/v1/repos/{}/{}".format(
            app.config["GITEA_INSTANCE_DOMAIN"],
            repo_owner,
            repo_name,
        ),
        json={
            "website": new_github_repo_url,
        },
    )

    gitea_push_target_result = gitea.post(
        "https://{}/api/v1/repos/{}/{}/push_mirrors".format(
            app.config["GITEA_INSTANCE_DOMAIN"],
            repo_owner,
            repo_name
        ),
        json={
            "interval": "8h0m0s",
            "remote_address": new_github_repo_url,
            "remote_password": app.config["GITHUB_ACCESS_TOKEN"],
            "remote_username": repo_owner,
            "sync_on_commit": True,
        },
    )

    gitea_force_target_push = gitea.post(
        "https://{}/api/v1/repos/{}/{}/push_mirrors-sync".format(
            app.config["GITEA_INSTANCE_DOMAIN"],
            repo_owner,
            repo_name
        ),
    )

    github_create_webhook_result = github.post(
        "https://api.github.com/repos/{}/{}/hooks".format(
            repo_owner,
            repo_name,
        ),
        json={
            "name": "web",
            "config": {
                "url": "https://{}/bridge/endpoints/github/issue".format(
                    app.config["GITEA_INSTANCE_DOMAIN"]
                ),
                "content_type": "json",
            },
            "events": [
                "issues", "issue_comment",
            ],
        },
    )

    gitea_create_webhook_result = gitea.post(
        "https://{}/api/v1/repos/{}/{}/hooks".format(
            app.config["GITEA_INSTANCE_DOMAIN"],
            repo_owner,
            repo_name,
        ),
        json={
            "active": True,
            "type": "gitea",
            "config": {
                "content_type": "json",
                "url": "https://{}/bridge/endpoints/gitea/issue".format(
                    app.config["GITEA_INSTANCE_DOMAIN"],
                ),
                "http_method": "post",
            },
            "events": [
                "issues", "issue_comment",
            ],
        },
    )

    return ''

@app.route("/bridge/endpoints/gitea/issue", methods=["POST"])
def gitea_handle_issue_action():
    """
        firstly, check if the sentinal is in the issue body
            - if it is, then stop processing the event
              (we don't want infinite loops)
        if we've opened an issue:
            - create a new one on the Github side
            - make it relate to the Gitea one
            - make the Gitea one related to the Github one
        
        if we've commented:
            - add a comment to the cooresponding Github issue

        if we've closed:
            - add a cooresponding comment and close the Github issue
    """

    gitea = Gitea(app.config["GITEA_ACCESS_TOKEN"])
    github = Github(app.config["GITHUB_ACCESS_TOKEN"])

    data = request.json

    try:
        event_type = data["action"]

        repo_owner = data["repository"]["owner"]["login"]
        repo_name = data["repository"]["name"]
        issue_user = data["issue"]["user"]["login"]
        issue_user_url = "https://{}/{}".format(
            app.config["GITEA_INSTANCE_DOMAIN"],
            issue_user,
        )
        issue_number = data["issue"]["number"]

        if event_type == "opened": # new issue created
            event_title = data["issue"]["title"]
            event_body = data["issue"]["body"]
        elif event_type == "created": # new comment on that issue
            event_title = None
            event_body = data["comment"]["body"]
        elif event_type == "closed": # issue closed
            event_title = None
            event_body = data["issue"]["body"]

        event_url = data["issue"]["url"]

    except KeyError as e:
        print(e, type(e))
        abort(400) # the data isn't formatted correctly

    if issue_sentinel in event_body:
        return ''

    if event_type == "opened":
        issue_header = "*This issue has automatically been created by [`gitea-github-sync`](https://{}/bridge/about) on behalf of [{}]({}).*".format(
            app.config["GITEA_INSTANCE_DOMAIN"],
            issue_user,
            issue_user_url,
        )

        issue_footer = """
<details>
    <summary>Internal issue metadata</summary>

    {}
</details>
        """.format(generate_sentinel(event_url))

        issue_body = "\n\n".join([
            issue_header,
            event_body,
            issue_footer
        ])
        
        github_create_issue_result = github.post(
            "https://api.github.com/repos/{}/{}/issues".format(
                repo_owner,
                repo_name,
            ),
            json={
                "title": event_title,
                "body": issue_body,
            },
        )
        
        returned_data = github_create_issue_result.json()
        issue_comment_body = """
*This issue is being mirrored on Github [here]({}).*

<details>
    <summary>Internal issue metadata</summary>

    {}
</details>
        """.format(
            returned_data["html_url"],
            generate_sentinel(returned_data["url"])
        )

        gitea_issue_comment_result = gitea.post(
            "https://{}/api/v1/repos/{}/{}/issues/{}/comments".format(
                app.config["GITEA_INSTANCE_DOMAIN"],
                repo_owner,
                repo_name,
                issue_number,
            ),
            json={
                "body": issue_comment_body,
            },
        )

        return ''