from flask import Flask
from flask import request
from flask import redirect
from flask import abort

app = Flask(__name__)
app.config.from_envvar('GIT_BRIDGE_SETTINGS')

@app.route("/bridge")
def index():
    return "you've reached the main page for an internal service. congrats!"