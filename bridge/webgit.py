from typing import Any
from dataclasses import dataclass, field

import requests
from requests import Request, Session
from requests.exceptions import HTTPError

from flask import abort

@dataclass
class WebgitClient:
    """
    A quite thin wrapper around various code forges' REST APIs.
    Designed to be subclassed.
    """
    api_token: str
    headers: Any = field(init=False)
    api_prefix: str = field(init=False)

    def _post_request(self, request_obj):
        try:
            request_obj.raise_for_status()
        except HTTPError as e:
            print("An exception occured: {}({})".format(
                type(e).__name__, e
            ))
            abort(500)

    def _request_wrapper(self, method, *args, **kwargs):
        s = Session()
        r = Request(method, *args, **kwargs, headers=self.headers)
        prepped = s.prepare_request(r)
        settings = s.merge_environment_settings(prepped.url, {}, None, None, None)
        r = s.send(prepped, **settings)

        self._post_request(r)
        return r


    def post(self, *args, **kwargs):
        return self._request_wrapper("POST", *args, **kwargs)

    def patch(self, *args, **kwargs):
        return self._request_wrapper("PATCH", *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._request_wrapper("DELETE", *args, **kwargs)

    def create_repo(self, name, description):
        return self.post(
            self.api_prefix + "/user/repos",
            json={
                "name": name,
                "description": description,
            },
        )
    
    def create_issue(self, owner, repo_name, title, body):
        return self.post(
            self.api_prefix + "/repos/{}/{}/issues".format(
                owner,
                repo_name,
            ),
            json={
                "title": title,
                "body": body,
            },
        )

    def leave_comment_on_issue_by_number(self, owner, repo_name, issue_number, body):
        return self.post(
            self.api_prefix + "/repos/{}/{}/issues/{}/comments".format(
                owner,
                repo_name,
                issue_number,
            ),
            json={
                "body": body,
            },
        )

    def leave_comment_on_issue_by_url(self, url, body):
        return self.post(
            url + "/comments",
            json={
                "body": body,
            },
        )

    def close_issue_by_number(self, owner, repo_name, issue_number):
        return self.patch(
            self.api_prefix + "/repos/{}/{}/issues/{}".format(
                owner,
                repo_name,
                issue_number,
            ),
            json={
                "state": "closed",
            },
        )

    def close_issue_by_url(self, url):
        return self.patch(
            url,
            json={
                "state": "closed",
            },
        )

    def delete_repo(self, owner, repo_name):
        return self.delete(
            self.api_prefix + "/repos/{}/{}".format(owner, repo_name)
        )

@dataclass
class Github(WebgitClient):
    """
    A quite thin wrapper around Github's REST API.
    """
    def __post_init__(self):
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": "token " + self.api_token,
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.api_prefix = "https://api.github.com"

    def create_webhook(self, owner, repo_name, http_endpoint, events: list[str]):
        return self.post(
            self.api_prefix + "/repos/{}/{}/hooks".format(
                owner,
                repo_name,
            ),
            json={
                "name": "web",
                "config": {
                    "url": http_endpoint,
                    "content_type": "json",
                },
                "events": events,
            },
        )

@dataclass
class Gitea(WebgitClient):
    """
    A quite thin wrapper around Gitea's REST API.
    """
    instance_name: str
    
    def __post_init__(self):
        self.headers = {
            "Authorization": "token " + self.api_token,
        }
        self.api_prefix = "https://{}/api/v1".format(self.instance_name)

    def add_push_target(self, owner, repo_name, address, username, password):
        return self.post(
            self.api_prefix + "/repos/{}/{}/push_mirrors".format(
                owner, repo_name
            ),
            json={
                "interval": "8h0m0s",
                "remote_address": address,
                "remote_password": password,
                "remote_username": username,
                "sync_on_commit": True,
            },
        )

    def force_push_target(self, owner, repo_name):
        return self.post(
            self.api_prefix + "/repos/{}/{}/push_mirrors-sync".format(
                owner,
                repo_name
            ),
        )

    def create_webhook(self, owner, repo_name, http_endpoint, events: list[str]):
        return self.post(
            self.api_prefix + "/repos/{}/{}/hooks".format(
                owner,
                repo_name,
            ),
            json={
                "config": {
                    "url": http_endpoint,
                    "content_type": "json",
                },
                "events": events,
                "type": "gitea",
            },
        )
