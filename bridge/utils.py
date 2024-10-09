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