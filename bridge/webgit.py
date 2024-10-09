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

@dataclass
class Gitea(WebgitClient):
    """
    A quite thin wrapper around Gitea's REST API.
    """
    def __post_init__(self):
        self.headers = {
            "Authorization": "token " + self.api_token,
        }
