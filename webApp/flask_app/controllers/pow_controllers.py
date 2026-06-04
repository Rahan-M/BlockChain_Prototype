from flask import request, jsonify, Response
import json, asyncio, websockets
from collections import OrderedDict
from webApp.blockchain.pow import p2p, blockchain_structures
from ecdsa import VerifyingKey, MalformedPointError, curves
from ..app import set_consensus
import sys, traceback, os

peer_instance:p2p.Peer=None
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
        miner_bool=p2p.strtobool(miner)
        # thread=threading.Thread(target=_start_peer_in_background,args=(host, port, name, miner_bool))
        # thread.daemon=True
        # thread.start()
        peer_instance = p2p.Peer(host, port, name, miner_bool, persistent_load, persistent_save)
        peer_instance.start_blockchain()

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

        if not(name and port and host and miner and bootstrap_host and bootstrap_port):
            return jsonify({"error": "Missing fields"}, 409)

        if peer_instance:
            return jsonify({"error": "One peer is already running. Stop it to run another one"}, 409)
        
        miner_bool=p2p.strtobool(miner)
        peer_instance = p2p.Peer(host, port, name, miner_bool, persistent_load, persistent_save)
        set_consensus('pow')
        peer_instance.connect_to_blockchain(bootstrap_host, bootstrap_port)

        return jsonify({"success":True ,"message": f"Peer '{name}' is being started in the background on {host}:{port}"})

    else:
        return jsonify({"success":False, "error": "Request must be JSON"})

async def stop_peer():
    global peer_instance
    if not peer_instance:
        return jsonify({"success":False, "error": "No peer running"})

    await peer_instance.stop()
    peer_instance=None
    set_consensus('')
    return jsonify({"success":True, "message": "Peer Stopped Successfully"})

def server_exists_check():
    global peer_instance
    print(peer_instance.server)
    print(asyncio.all_tasks())
    if(peer_instance.server):
        return jsonify({'success':True, 'message':'Server exists'})

    return jsonify({'success':False, 'message':"Server doesn't exist"})

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

def account_balance():
    global peer_instance
    if not peer_instance:
        return jsonify({"success":False, "error": "No node is running"}, 409)
    
    if not peer_instance.chain:
        return jsonify({"success":False, "error": "Chain hasn't been initialized"}, 409)
    
    try:
        print()
        amt = peer_instance.get_account_balance(peer_instance.wallet.public_key_pem, list(peer_instance.mem_pool))
        return jsonify({"success":True, "message":"succesful request", "account_balance": amt})
    except:
        return jsonify({"success":False, "error": "error while fetching account balance"}, 409)

def get_contracts():
    global peer_instance

    contracts = []
    for contract_id in peer_instance.contractsDB.contracts:
        contracts.append({
            "id": contract_id,
            "code": peer_instance.contractsDB.contracts[contract_id],
        })

    return jsonify({"success":True, "message":"succesful request", "contracts": contracts})

def get_status():
    global peer_instance

    return Response(
        json.dumps({
            "success": True,
            **peer_instance.get_my_info()
        }),
        mimetype="application/json"
    )

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
            "transactions": blockchain_structures.txs_to_json_digestable_form(block.transactions),
            "ts": block.ts,
            "nonce": block.nonce,
            "hash": block.hash,
            "miner": block.miner,
            "files": file_list,
        })

    return jsonify({"success":True, "message":"succesful request", "chain": chain_list})

def get_pending_transactions():
    global peer_instance

    pending_transactions = blockchain_structures.txs_to_json_digestable_form(list(peer_instance.mem_pool))

    return jsonify({"success":True, "message":"succesful request", "pending_transactions": pending_transactions})

def get_known_peers():
    global peer_instance

    known_peers_list = []
    for peer in peer_instance.known_peers.keys():
        known_peers_list.append({
            "name": peer_instance.known_peers[peer][0],
            "host": peer[0],
            "port": peer[1],
            "public_key": peer_instance.known_peers[peer][1],
        })

    return jsonify({"success":True, "message":"succesful request", "known_peers": known_peers_list})

async def uploadFileIPFS():
    global peer_instance
    if(not request.is_json):
        return jsonify({"success":False, "error": "Request must be JSON"})

    data=request.get_json()
    desc=data.get('desc')
    path=data.get('path')
    await peer_instance.upload_file(desc, path)

    #The output of the first method, os.path.join(), would be home/desktop/newFolder/my_story.txt on a Linux or macOS system. On a Windows system, it would automatically be home\desktop\newFolder\my_story.txt, correctly handling the different slash.
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
