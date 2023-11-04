import typing as t

import requests


def fetch_tags_from_docker_hub_repo(repo: str) -> t.List[str]:
    url = f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{repo}:pull"
    resp = requests.get(url)
    if not resp.ok:
        resp.raise_for_status()
    json = resp.json()
    token = json["token"]

    url = f"https://registry-1.docker.io/v2/{repo}/tags/list"
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
    )
    if not resp.ok:
        resp.raise_for_status()

    return resp.json()["tags"]
