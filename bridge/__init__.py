from flask import Flask
from flask import request
from flask import redirect
from flask import abort

import requests

from .webgit import Gitea, Github
from .utils import issue_sentinel, generate_sentinel, create_signature

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

    gitea = Gitea(
        api_token=app.config["GITEA_ACCESS_TOKEN"],
        instance_name=app.config["GITEA_INSTANCE_DOMAIN"]
    )
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

    if repo_action == "created":
        new_repo = github.create_repo(
            repo_name, repo_description
        )
        new_repo_url = new_repo.json()["html_url"]

        gitea.add_push_target(
            repo_owner, repo_name, new_repo_url, repo_owner,
            app.config["GITHUB_ACCESS_TOKEN"]
        )
        gitea.force_push_target(
            repo_owner,
            repo_name
        )

        github.create_webhook(
            repo_owner,
            repo_name,
            "https://{}/bridge/endpoints/github/issue".format(
                app.config["GITEA_INSTANCE_DOMAIN"]
            ),
            ["issues", "issue_comment"]
        )
        gitea.create_webhook(
            repo_owner,
            repo_name,
            "https://{}/bridge/endpoints/gitea/issue".format(
                app.config["GITEA_INSTANCE_DOMAIN"]
            ),
            ["issues", "issue_comment"]
        )

    elif repo_action == "deleted":
        github.delete_repo(repo_owner, repo_name)

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

    gitea = Gitea(
        api_token=app.config["GITEA_ACCESS_TOKEN"],
        instance_name=app.config["GITEA_INSTANCE_DOMAIN"]
    )
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

    issue_sentinel_present = issue_sentinel in event_body

    if event_type == "opened" and not issue_sentinel_present:
        issue_footer = create_signature(
            issue_user,
            issue_user_url,
            app.config["GITEA_INSTANCE_DOMAIN"],
            event_url,
        )

        issue_body = "\n\n".join([
            event_body,
            issue_footer
        ])
        
        new_issue = github.create_issue(
            repo_owner,
            repo_name,
            event_title,
            issue_body,
        )

        returned_data = new_issue.json()
        issue_comment_body = create_signature(
            "mirrored",
            returned_data["html_url"],
            app.config["GITEA_INSTANCE_DOMAIN"],
            returned_data["url"],
        )

        gitea.leave_comment_on_issue_by_number(
            repo_owner,
            repo_name,
            issue_number,
            issue_comment_body,
        )

    elif event_type == "created" and not issue_sentinel_present:
        comment_user = data["comment"]["user"]["login"]
        comment_user_url = "https://{}/{}".format(
            app.config["GITEA_INSTANCE_DOMAIN"],
            comment_user,
        )
        comment_footer = create_signature(
            comment_user,
            comment_user_url,
            app.config["GITEA_INSTANCE_DOMAIN"],
            event_url,
        )
        comment_body = "\n\n".join([
            event_body,
            comment_footer,
        ])

        github.leave_comment_on_issue_by_number(
            repo_owner,
            repo_name,
            issue_number,
            comment_body,
        )
    
    elif event_type == "closed":
        github.close_issue_by_number(
            repo_owner,
            repo_name,
            issue_number,
        )
    
    return ''

@app.route("/bridge/endpoints/github/issue", methods=["POST"])
def github_handle_issue_action():
    gitea = Gitea(
        api_token=app.config["GITEA_ACCESS_TOKEN"],
        instance_name=app.config["GITEA_INSTANCE_DOMAIN"]
    )
    github = Github(app.config["GITHUB_ACCESS_TOKEN"])

    data = request.json

    try:
        event_type = data["action"]

        repo_owner = data["repository"]["owner"]["login"]
        repo_name = data["repository"]["name"]
        issue_user = data["issue"]["user"]["login"]
        issue_user_url = "https://github.com/{}".format(
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

        if not event_body: event_body = ""
        event_url = data["issue"]["url"]

    except KeyError as e:
        print(e, type(e))
        abort(400) # the data isn't formatted correctly

    issue_sentinel_present = issue_sentinel in event_body

    if event_type == "opened" and not issue_sentinel_present:
        issue_footer = create_signature(
            issue_user,
            issue_user_url,
            app.config["GITEA_INSTANCE_DOMAIN"],
            event_url,
        )
        issue_body = "\n\n".join([
            event_body,
            issue_footer
        ])

        new_issue = gitea.create_issue(
            repo_owner,
            repo_name,
            event_title,
            issue_body
        )
        
        returned_data = new_issue.json()
        issue_comment_body = create_signature(
            "mirrored",
            returned_data["html_url"],
            app.config["GITEA_INSTANCE_DOMAIN"],
            returned_data["url"],
        )

        github.leave_comment_on_issue_by_number(
            repo_owner,
            repo_name,
            issue_number,
            issue_comment_body,
        )

    elif event_type == "created" and not issue_sentinel_present:
        comment_user = data["comment"]["user"]["login"]
        comment_user_url = "https://github.com/{}".format(
            comment_user,
        )
        comment_footer = create_signature(
            comment_user,
            comment_user_url,
            app.config["GITEA_INSTANCE_DOMAIN"],
            event_url,
        )

        comment_body = "\n\n".join([
            event_body,
            comment_footer,
        ])

        gitea.leave_comment_on_issue_by_number(
            repo_owner,
            repo_name,
            issue_number,
            comment_body
        )
        
    elif event_type == "closed":
        gitea.close_issue_by_number(
            repo_owner,
            repo_name,
            issue_number,
        )
    
    return ''
