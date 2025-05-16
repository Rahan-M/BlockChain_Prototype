from flask import Flask, Response
from collections import OrderedDict
import json
from blochain_structures import Chain, txs_to_json_digestable_form


def create_flask_app(peer):
    app = Flask(__name__)

    @app.route("/status", methods=["GET"])
    def get_status():
        chainList = []
        for block in Chain.instance.chain:
            chainList.append({
                "id": block.id,
                "prevHash": block.prevHash,
                "transactions": txs_to_json_digestable_form(block.transactions),
                "ts": block.ts,
                "nonce": block.nonce,
                "hash": block.hash
            })
        return Response(
            json.dumps(OrderedDict([
                ("name", peer.name),
                ("host", peer.host),
                ("port", peer.port),
                ("connected_peers", list(map(lambda x: peer.known_peers[x][0]+":"+x[0]+":"+str(x[1])+":"+peer.known_peers[x][1], peer.known_peers.keys()))),
                ("mempool", txs_to_json_digestable_form(list(peer.mem_pool))),
                ("chain", chainList)
            ])),
            mimetype='application/json'
        )
    
    return app
    
def run_flask_app(app, port):
    app.run(host="0.0.0.0", port=port + 20)