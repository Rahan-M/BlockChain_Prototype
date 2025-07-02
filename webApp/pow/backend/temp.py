from flask import Flask, Response
from collections import OrderedDict
import json
from blochain_structures import Wallet
from flask_cors import CORS

def create_flask_app():
    app = Flask(__name__)
    CORS(app)
    
    @app.route("/create_keys", methods=["GET"])
    def get_status():
        wallet=Wallet()
        return Response(
            json.dumps(OrderedDict([
                ("sk", wallet.private_key_pem),
                ("vk",wallet.public_key)
            ])),
            mimetype='application/json'
        )
    
    return app
    
app=create_flask_app()
app.run(host="0.0.0.0", port=5020)