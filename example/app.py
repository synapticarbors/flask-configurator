from flask import Flask, jsonify
from flask_configurator import Configurator


app = Flask(__name__)
config = Configurator(app)


@app.route("/")
def index():
    return jsonify(config)
