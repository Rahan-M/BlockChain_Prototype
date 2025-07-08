from flask import request, jsonify, Response
import json, asyncio
from collections import OrderedDict
from blockchain.pow import p2p, blockchain_structures

from ..app import _start_peer_in_background
import threading

async def start_new_blockchain():
    from ..app import peer_instance
    if request.is_json:
        data = request.get_json()
        name = data.get('name')
        port = int(data.get('port'))
        host = data.get('host')
        miner = data.get('miner')

        if peer_instance:
            return jsonify({"error": f"One peer is already running. Stop it to run another one"}, 409)
        
        miner_bool=p2p.strtobool(miner)
        # Use the _start_peer_in_background function imported from __init__.py
        # I'm storing this in this variable because gemini hypothesized that will stop the
        # the spontaneous cancelling of the node
        thread=threading.Thread(target=_start_peer_in_background,args=(host, port, name, miner_bool))
        thread.daemon=True
        thread.start()
        return jsonify({"success":True ,"message": f"Peer '{name}' is being started in the background on {host}:{port}"})
    else:
        return jsonify({"success":False, "error": "Request must be JSON"})
    
async def connect_to_blockchain():
    from ..app import peer_instance
    if request.is_json:
        data = request.get_json()
        name = data.get('name')
        port = int(data.get('port'))
        host = data.get('host')
        miner = data.get('miner')
        bootstrap_port = int(data.get('bootstrap_port'))
        bootstrap_host = data.get('bootstrap_host')


        if peer_instance:
            return jsonify({"error": f"One peer is already running. Stop it to run another one"}, 409)
        
        miner_bool=p2p.strtobool(miner)
        # Use the _start_peer_in_background function imported from __init__.py
        # I'm storing this in this variable because gemini hypothesized that will stop the
        # the spontaneous cancelling of the node
        thread=threading.Thread(target=_start_peer_in_background,args=(host, port, name, miner_bool, bootstrap_host, bootstrap_port))
        thread.daemon=True
        thread.start()
        return jsonify({"success":True ,"message": f"Peer '{name}' is being started in the background on {host}:{port}"})
    else:
        return jsonify({"success":False, "error": "Request must be JSON"})

def account_balance():
    from ..app import peer_instance
    if not peer_instance:
        return jsonify({"success":False, "error": "No node is running"}, 409)
    
    if not peer_instance.chain:
        return jsonify({"success":False, "error": "Chain hasn't been initialized"}, 409)
    
    try:
        print()
        amt=peer_instance.chain.calc_balance(peer_instance.wallet.public_key_pem, list(peer_instance.mem_pool))
        return jsonify({"success":True, "message":"succesful request", "account_balance": amt})
    except:
        return jsonify({"success":False, "error": "error while fetching accoutn balance"}, 409)

def get_status():
        from ..app import peer_instance
        chain_list = []
        for block in peer_instance.chain.chain:
            chain_list.append(block.to_dict())
        outbound_peers_list = []
        for outbound_peer in peer_instance.outbound_peers:
            outbound_peers_list.append({
                "addr": outbound_peer[0],
                "port": outbound_peer[1]
            })
        return Response(
            json.dumps(OrderedDict([
                ("name", peer_instance.name),
                ("host", peer_instance.host),
                ("port", peer_instance.port),
                ("known_peers", list(map(lambda x: peer_instance.known_peers[x][0]+":"+x[0]+":"+str(x[1])+":"+peer_instance.known_peers[x][1], peer_instance.known_peers.keys()))),
                ("outbound_peers", outbound_peers_list),
                ("client_connections", list(ws.remote_address[1] for ws in peer_instance.client_connections)),
                ("server_connections", list(ws.remote_address[1] for ws in peer_instance.server_connections)),
                ("mempool", blockchain_structures.txs_to_json_digestable_form(list(peer_instance.mem_pool))),
                ("chain", chain_list)
            ])),
            mimetype='application/json'
        )