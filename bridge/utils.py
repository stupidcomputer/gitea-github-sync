import base64

def to_base64(s: str) -> str:
    return base64.b64encode(
        s.encode("utf-8")
    ).decode("utf-8")

def from_base64(s: str) -> str:
    return base64.b64decode(
        s.encode("utf-8")
    ).decode("utf-8")

issue_sentinel = "GITEA_GITHUB_ISSUE_SYNC_SENTINEL"

def generate_sentinel(url: str) -> str:
    return ' '.join([issue_sentinel, to_base64(url)])

def create_signature(
    username: str,
    username_url: str,
    domain_base: str,
    url_to_encode: str,
    ):
    return """

---

[{}]({}) via [gitea-github-sync](https://{}/bridge/about)

<details>
    <summary>Internal information</summary>

    {}
</details>
    """.format(
        username,
        username_url,
        domain_base,
        generate_sentinel(url_to_encode),
    )