from flask import Flask
from flask_cors import CORS

def create_flask_app(peer):
    app = Flask(__name__)
    CORS(app)

    return app
