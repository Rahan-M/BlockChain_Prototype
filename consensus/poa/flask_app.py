from flask import Flask, Response
from collections import OrderedDict
import json
from blochain_structures import Chain, txs_to_json_digestable_form


def create_flask_app(peer):
    app = Flask(__name__)

    @app.route("/status", methods=["GET"])
    def get_status():
        chain_list = []
        for block in Chain.instance.chain:
            chain_list.append({
                "id": block.id,
                "prevHash": block.prevHash,
                "transactions": txs_to_json_digestable_form(block.transactions),
                "ts": block.ts,
                "hash": block.hash,
                "miner_node_id": block.miner_node_id,
                "miner_public_key": block.miner_public_key,
                "miners_list": block.miners_list,
                "signature": block.signature,
            })
        outbound_peers_list = []
        for outbound_peer in peer.outbound_peers:
            outbound_peers_list.append({
                "addr": outbound_peer[0],
                "port": outbound_peer[1]
            })
        files = {}
        for block in Chain.instance.chain:
            if block.files:
                files.update(block.files)
        return Response(
            json.dumps(OrderedDict([
                ("name", peer.name),
                ("host", peer.host),
                ("port", peer.port),
                ("mining_round", peer.round),
                ("is_miner", peer.miner),
                ("admin_id", peer.admin_id),
                ("node_id", peer.node_id),
                ("miners", peer.miners),
                ("name to node id dict", peer.name_to_node_id_dict),
                ("node_id_to_name_dict", peer.node_id_to_name_dict),
                ("known_peers", list(map(lambda x: peer.known_peers[x][0]+":"+x[0]+":"+str(x[1])+":"+peer.known_peers[x][1], peer.known_peers.keys()))),
                ("outbound_peers", outbound_peers_list),
                ("client_connections", list(ws.remote_address[1] for ws in peer.client_connections)),
                ("server_connections", list(ws.remote_address[1] for ws in peer.server_connections)),
                ("mempool", txs_to_json_digestable_form(list(peer.mem_pool))),
                ("chain", chain_list),
                ("contracts", peer.contractsDB.contracts),
                ("files", files),
            ])),
            mimetype='application/json'
        )
    
    return app
    
def run_flask_app(app, port):
    app.run(host="0.0.0.0", port=port + 20)