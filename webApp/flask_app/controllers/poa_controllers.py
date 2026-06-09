from flask import request, jsonify, Response
import json, asyncio, websockets
from collections import OrderedDict
from webApp.blockchain.peer.poa_peer import PoAPeer
from webApp.blockchain.blockchain_structures.utils import txs_to_json_digestable_form

from ecdsa import VerifyingKey, MalformedPointError, curves
from ..app import set_consensus
import sys, traceback, os, copy

peer_instance = None
GAS_PRICE = 0.001 # coin per gas unit
BASE_DEPLOY_COST = 5

async def start_new_blockchain():
    global peer_instance
    if request.is_json:
        data = request.get_json()
        name = data.get('name')
        port = int(data.get('port'))
        host = data.get('host')
        persistent_load = data.get('persistent_load')
        persistent_save = data.get('persistent_save')

        if peer_instance:
            return jsonify({"error": f"One peer is already running. Stop it to run another one"}, 409)
        
        if not(name and port and host):
            return jsonify({"error": "Missing fields"}, 409)

        set_consensus('poa')
        
        peer_instance = PoAPeer(host, port, name, persistent_load, persistent_save)

        await peer_instance.start_blockchain()

        return jsonify({"success":True ,"message": f"Peer '{name}' is being started in the background on {host}:{port}"})
    else:
        return jsonify({"success":False, "error": "Request must be JSON"})

async def connect_to_blockchain():
    global peer_instance
    if request.is_json:
        data = request.get_json()
        name = data.get('name')
        port = int(data.get('port'))
        host = data.get('host')
        persistent_load = data.get('persistent_load')
        persistent_save = data.get('persistent_save')
        bootstrap_port = int(data.get('bootstrap_port'))
        bootstrap_host = data.get('bootstrap_host')

        if not(name and port and host and bootstrap_host and bootstrap_port):
            return jsonify({"error": "Missing fields"}, 409)

        if peer_instance:
            return jsonify({"error": "One peer is already running. Stop it to run another one"}, 409)

        peer_instance = PoAPeer(host, port, name, persistent_load, persistent_save)
        await peer_instance.connect_to_blockchain(bootstrap_host, bootstrap_port)
        set_consensus('poa')
        

        return jsonify({"success":True ,"message": f"Peer '{name}' is being started in the background on {host}:{port}"})

    else:
        return jsonify({"success":False, "error": "Request must be JSON"})

async def add_transaction():
    global peer_instance

    if not request.is_json:
        return jsonify({
            "success": False,
            "error": "Request must be JSON"
        })

    data = request.get_json()

    public_key = data.get("public_key")
    payload = data.get("payload")

    if public_key is None or payload is None:
        return jsonify({
            "success": False,
            "error": "Public Key or Payload Not Found"
        })

    try:

        # Contract Deployment
        if public_key == "deploy":

            contract_code = payload[0]

            await peer_instance.deploy_contract(
                contract_code
            )

        # Contract Invocation
        elif public_key == "invoke":

            contract_id = payload[0]
            func_name = payload[1]
            args = payload[2]

            await peer_instance.invoke_contract(
                contract_id,
                func_name,
                args
            )

        # Normal Transfer
        else:

            amount = float(payload)

            await peer_instance.send_money(
                amount,
                public_key
            )

        return jsonify({
            "success": True,
            "message": "Transaction Submitted"
        })

    except (IndexError, ValueError, TypeError):
        return jsonify({
            "success": False,
            "error": "Invalid Payload"
        })

def get_chain():
    global peer_instance
    chain = peer_instance.chain.chain

    chain_list = []
    for block in chain:
        file_list = []
        for cid, desc in block.files.items():
            file_list.append({
                "cid": cid,
                "desc": desc,
            })
        chain_list.append({
            "id": block.id,
            "prevHash": block.prevHash,
            "transactions": txs_to_json_digestable_form(block.transactions),
            "ts": block.ts,
            "hash": block.hash,
            "miner_node_id": block.miner_node_id,
            "miner_public_key":  block.miner_public_key,
            "miners_list": block.miners_list,
            "files": file_list,
        })

    return jsonify({"success":True, "message":"succesful request", "chain": chain_list})

# done

def get_states():
    global peer_instance

    return jsonify({
        "success":True,
        "message":"succesful request",
        "states": peer_instance.get_contracts_state()
    })

def get_contracts():
    global peer_instance

    return jsonify({
        "success":True,
        "message":"succesful request",
        "contracts": peer_instance.get_contracts()
    })

def server_exists_check():
    global peer_instance

    print(peer_instance.server)
    print(asyncio.all_tasks())
    
    if(peer_instance.server):
        return jsonify({'success':True, 'message':'Server exists'})

    return jsonify({'success':False, 'message':"Server doesn't exist"})

async def stop_peer():
    global peer_instance

    if not peer_instance:
        return jsonify({"success":False, "error": "No peer running"})

    await peer_instance.stop()
    peer_instance = None
    set_consensus('')

    return jsonify({"success":True, "message": "Peer Stopped Successfully"})

def account_balance():
    global peer_instance

    if not peer_instance:
        return jsonify({"success":False, "error": "No node is running"}, 409)
    
    if not peer_instance.chain.chain == []:
        return jsonify({"success":False, "error": "Chain hasn't been initialized"}, 409)
    
    try:
        amt = peer_instance.get_account_balance()
        return jsonify({
            "success":True,
            "message":"succesful request",
            "account_balance": amt
        })
    except:
        return jsonify({"success":False, "error": "error while fetching account balance"}, 409)

def get_status():
    global peer_instance

    return Response(
        json.dumps({
            "success": True,
            **peer_instance.get_my_info()
        }),
        mimetype="application/json"
    )

def get_pending_transactions():
    global peer_instance

    return jsonify({
        "success":True,
        "message":"succesful request",
        "pending_transactions": peer_instance.get_pending_transactions()
    })

def get_known_peers():
    global peer_instance

    return jsonify({
        "success":True,
        "message":"succesful request",
        "known_peers": peer_instance.get_known_peers()
    })

def get_current_miners():
    global peer_instance

    miners_node_id_list = peer_instance.get_current_miners_list()
    current_miners_list = []
    for node_id in miners_node_id_list:
        name = peer_instance.node_id_to_name_dict[node_id]
        public_key = None
        if node_id == peer_instance.node_id:
            public_key = peer_instance.wallet.public_key_pem
        else:
            public_key = peer_instance.name_to_public_key_dict[name]
        current_miners_list.append({
            "node_id": node_id,
            "name": name,
            "public_key": public_key,
        })

    return jsonify({"success":True, "message":"succesful request", "current_miners": current_miners_list})

async def add_miner():
    global peer_instance
    if(not request.is_json):
        return jsonify({"success":False, "error": "Request must be JSON"})

    data=request.get_json()
    node_id = data.get('node_id')
    if(not node_id):
        return jsonify({"success":False, "error": "Node ID not found"})
    
    if(not peer_instance.is_found_node_id(node_id)):
        return jsonify({"success":False, "error": "No node with given node id"})
    
    miners_list = None
    if peer_instance.miners:
        miners_list = copy.deepcopy(peer_instance.miners[-1][0])
    else:
        miners_list = copy.deepcopy(peer_instance.chain.chain[-1].miners_list)

    if node_id in miners_list:
        return jsonify({"success":False, "error": "Miner with given Node ID is already a miner"})
    
    miners_list.append(node_id)
    peer_instance.miners.append([miners_list, len(peer_instance.chain.chain) + 3])
    await peer_instance.broadcast_miners_list(miners_list, len(peer_instance.chain.chain) + 3)

    return jsonify({"success":True, "message": "Miner Added"})
    
async def remove_miner():
    global peer_instance
    if(not request.is_json):
        return jsonify({"success":False, "error": "Request must be JSON"})

    data=request.get_json()
    node_id = data.get('node_id')
    if(not node_id):
        return jsonify({"success":False, "error": "Node ID not found"})
    
    if(not peer_instance.is_found_node_id(node_id)):
        return jsonify({"success":False, "error": "No node with given node id"})
    
    miners_list = None
    if peer_instance.miners:
        miners_list = copy.deepcopy(peer_instance.miners[-1][0])
    else:
        miners_list = copy.deepcopy(peer_instance.chain.chain[-1].miners_list)

    if node_id not in miners_list:
        return jsonify({"success":False, "error": "Miner with given Node ID is already not a miner"})
    
    miners_list.remove(node_id)
    peer_instance.miners.append([miners_list, len(peer_instance.chain.chain) + 3])
    await peer_instance.broadcast_miners_list(miners_list, len(peer_instance.chain.chain) + 3)

    return jsonify({"success":True, "message": "Miner Removed"})

def get_latest_miners():
    global peer_instance
    
    miners_node_id_list = None
    if peer_instance.miners:
        miners_node_id_list = copy.deepcopy(peer_instance.miners[-1][0])
    else:
        miners_node_id_list = copy.deepcopy(peer_instance.chain.chain[-1].miners_list)

    latest_miners_list = []
    for node_id in miners_node_id_list:
        name = peer_instance.node_id_to_name_dict[node_id]
        public_key = None
        if node_id == peer_instance.node_id:
            public_key = peer_instance.wallet.public_key_pem
        else:
            public_key = peer_instance.name_to_public_key_dict[name]
        latest_miners_list.append({
            "node_id": node_id,
            "name": name,
            "public_key": public_key,
        })

    return jsonify({"success":True, "message":"succesful request", "laminers": latest_miners_list})

def get_not_latest_miners():
    global peer_instance
    
    miners_node_id_list = None
    if peer_instance.miners:
        miners_node_id_list = copy.deepcopy(peer_instance.miners[-1][0])
    else:
        miners_node_id_list = copy.deepcopy(peer_instance.chain.chain[-1].miners_list)

    not_latest_miners_list = []
    for node_id in peer_instance.node_id_to_name_dict:
        if node_id not in miners_node_id_list:
            name = peer_instance.node_id_to_name_dict[node_id]
            public_key = None
            if node_id == peer_instance.node_id:
                public_key = peer_instance.wallet.public_key_pem
            else:
                public_key = peer_instance.name_to_public_key_dict[name]
            not_latest_miners_list.append({
                "node_id": node_id,
                "name": name,
                "public_key": public_key,
            })

    return jsonify({"success":True, "message":"succesful request", "nlaminers": not_latest_miners_list})

async def uploadFileIPFS():
    global peer_instance

    if(not request.is_json):
        return jsonify({"success":False, "error": "Request must be JSON"})

    data=request.get_json()
    desc=data.get('desc')
    path=data.get('path')

    await peer_instance.upload_file(desc, path)

    return jsonify({"success":True, "message": "File Uploaded"})

def downloadFileIPFS():
    global peer_instance

    if(not request.is_json):
        return jsonify({"success":False, "error": "Request must be JSON"})

    data=request.get_json()
    cid=data.get('cid')
    path=data.get('path')
    name=data.get('name')

    full_path=os.path.join(path, name)
    print(full_path)

    peer_instance.download_file(cid, full_path)
    
    return jsonify({"success":True, "message": "File Downloaded"})
