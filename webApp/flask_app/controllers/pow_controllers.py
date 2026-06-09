from flask import request, jsonify, Response
import json, asyncio, websockets
from collections import OrderedDict
from webApp.blockchain.peer.pow_peer import PoWPeer
from webApp.blockchain.blockchain_structures.utils import txs_to_json_digestable_form
from webApp.blockchain.utils import strtobool
from ecdsa import VerifyingKey, MalformedPointError, curves
from ..app import set_consensus
import sys, traceback, os

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
        miner = data.get('miner')
        persistent_load = data.get('persistent_load')
        persistent_save = data.get('persistent_save')

        if peer_instance:
            return jsonify({"error": f"One peer is already running. Stop it to run another one"}, 409)
        
        if not(name and port and host and miner):
            return jsonify({"error": "Missing fields"}, 409)

        set_consensus('pow')
        miner_bool=strtobool(miner)
        # thread=threading.Thread(target=_start_peer_in_background,args=(host, port, name, miner_bool))
        # thread.daemon=True
        # thread.start()
        peer_instance = PoWPeer(host, port, name, miner_bool, persistent_load, persistent_save)
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
        miner = data.get('miner')
        persistent_load = data.get('persistent_load')
        persistent_save = data.get('persistent_save')
        bootstrap_port = int(data.get('bootstrap_port'))
        bootstrap_host = data.get('bootstrap_host')

        if not(name and port and host and bootstrap_host and bootstrap_port):
            return jsonify({"error": "Missing fields"}, 409)

        if peer_instance:
            return jsonify({"error": "One peer is already running. Stop it to run another one"}, 409)
        
        miner_bool=strtobool(miner)
        peer_instance = PoWPeer(host, port, name, miner_bool, persistent_load, persistent_save)
        set_consensus('pow')
        await peer_instance.connect_to_blockchain(bootstrap_host, bootstrap_port)

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
            "nonce": block.nonce,
            "hash": block.hash,
            "miner": block.miner,
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
