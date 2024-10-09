import requests
import json

with open("data/gitea-issue-closed.json", "r") as file:
    data = json.loads(file.read())

r = requests.post("http://127.0.0.1:5000/bridge/endpoints/gitea/issue", json=data)
print(r.text)