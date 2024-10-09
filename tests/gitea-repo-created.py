import requests
import json

with open("data/gitea-repo-created.json", "r") as file:
    data = json.loads(file.read())

r = requests.post("http://127.0.0.1:5000/bridge/endpoints/gitea/repo", json=data)
print(r.text)