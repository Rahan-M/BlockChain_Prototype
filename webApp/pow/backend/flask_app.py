from flask import Flask, Response
from flask_cors import CORS
from collections import OrderedDict
import json
from blochain_structures import Chain, Wallet, txs_to_json_digestable_form

def create_flask_app(peer):
    app = Flask(__name__)
    CORS(app)
    
    @app.route("/")
    def say_hello():
        return "<h1>Hello</h1>"
   
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
    
    @app.route("/status", methods=["GET"])
    def get_status():
        chain_list = []
        for block in Chain.instance.chain:
            chain_list.append({
                "id": block.id,
                "prevHash": block.prevHash,
                "transactions": txs_to_json_digestable_form(block.transactions),
                "ts": block.ts,
                "nonce": block.nonce,
                "hash": block.hash
            })
        outbound_peers_list = []
        for outbound_peer in peer.outbound_peers:
            outbound_peers_list.append({
                "addr": outbound_peer[0],
                "port": outbound_peer[1]
            })
        return Response(
            json.dumps(OrderedDict([
                ("name", peer.name),
                ("host", peer.host),
                ("port", peer.port),
                ("known_peers", list(map(lambda x: peer.known_peers[x][0]+":"+x[0]+":"+str(x[1])+":"+peer.known_peers[x][1], peer.known_peers.keys()))),
                ("outbound_peers", outbound_peers_list),
                ("client_connections", list(ws.remote_address[1] for ws in peer.client_connections)),
                ("server_connections", list(ws.remote_address[1] for ws in peer.server_connections)),
                ("mempool", txs_to_json_digestable_form(list(peer.mem_pool))),
                ("chain", chain_list)
            ])),
            mimetype='application/json'
        )

    
    return app

app=create_flask_app()
app.run(host="0.0.0.0", port=5020)

