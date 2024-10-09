from flask import Flask
from flask import request
from flask import redirect
from flask import abort

import requests

app = Flask(__name__)
app.config.from_envvar('GIT_BRIDGE_SETTINGS')

@app.route("/bridge")
def index():
    return "you've reached the main page for an internal service. congrats!"

@app.route("/bridge/endpoints/gitea/repo", methods=["POST"])
def gitea_handle_repo_action():
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

    """
        Our plan of action for handling these events:
        - ignore deleting repositories -- this is a potentially destructive operation
          that *only* *the* *user* *should* *do*
        - create a cooresponding repo on github
        - create a push mirror to github so pushes to gitea get to github
        - create webhooks for issues (and in the future, pull requests) on both
          Gitea and Github ends
    """

    if not repo_action == "created":
        return ''

    github_created_repo_result = requests.post(
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
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "token " + app.config["GITHUB_ACCESS_TOKEN"],
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    try:
        github_created_repo_result.raise_for_status()
    except requests.exceptions.HTTPError:
        abort(500)

    new_github_repo_url = github_created_repo_result.json()["html_url"]

    gitea_add_github_repo_url_result = requests.patch(
        "https://{}/api/v1/repos/{}/{}".format(
            app.config["GITEA_INSTANCE_DOMAIN"],
            repo_owner,
            repo_name,
        ),
        json={
            "website": new_github_repo_url,
        },
        headers={
            "Authorization": "token " + app.config["GITEA_ACCESS_TOKEN"],
        },
    )

    try:
        gitea_add_github_repo_url_result.raise_for_status()
    except requests.exceptions.HTTPError:
        abort(500)

    gitea_push_target_result = requests.post(
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
        headers={
            "Authorization": "token " + app.config["GITEA_ACCESS_TOKEN"],
        },
    )

    try:
        gitea_push_target_result.raise_for_status()
    except requests.exceptions.HTTPError:
        abort(500)

    gitea_force_target_push = requests.post(
        "https://{}/api/v1/repos/{}/{}/push_mirrors-sync".format(
            app.config["GITEA_INSTANCE_DOMAIN"],
            repo_owner,
            repo_name
        ),
        headers={
            "Authorization": "token " + app.config["GITEA_ACCESS_TOKEN"],
        },
    )

    try:
        gitea_force_target_push.raise_for_status()
    except requests.exceptions.HTTPError:
        abort(500)

    github_create_webhook_result = requests.post(
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
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "token " + app.config["GITHUB_ACCESS_TOKEN"],
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    try:
        github_create_webhook_result.raise_for_status()
    except requests.exceptions.HTTPError:
        abort(500)

    gitea_create_webhook_result = requests.post(
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
        headers={
            "Authorization": "token " + app.config["GITEA_ACCESS_TOKEN"],
        },
    )
    
    try:
        gitea_create_webhook_result.raise_for_status()
    except requests.exceptions.HTTPError:
        abort(500)

    return ''