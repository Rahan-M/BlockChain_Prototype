from flask import request, jsonify, Response
import json, asyncio, websockets, base64
from typing import List, Dict
from datetime import datetime, timedelta
from collections import OrderedDict
from webApp.blockchain.pos import p2p, blockchain_structures
from ecdsa import VerifyingKey, MalformedPointError, curves
from ..app import set_consensus
import sys, traceback, os

peer_instance:p2p.Peer=None
GAS_PRICE = 0.001 # coin per gas unit
BASE_DEPLOY_COST = 5
EPOCH_TIME=60

async def start_new_blockchain():
    global peer_instance
    if request.is_json:
        data = request.get_json()
        name = data.get('name')
        port = int(data.get('port'))
        host = data.get('host')
        staker = data.get('miner')
        persistent_load = data.get('persistent_load')
        persistent_save = data.get('persistent_save')

        if peer_instance:
            return jsonify({"error": f"One peer is already running. Stop it to run another one"}, 409)
        
        if not(name and port and host and staker):
            return jsonify({"error": "Missing fields"}, 409)

        set_consensus('pos')
        staker_bool=p2p.strtobool(staker)
        peer_instance = p2p.Peer(host, port, name, staker_bool, persistent_load, persistent_save)
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
        staker = data.get('miner')
        persistent_load = data.get('persistent_load')
        persistent_save = data.get('persistent_save')
        bootstrap_port = int(data.get('bootstrap_port'))
        bootstrap_host = data.get('bootstrap_host')

        if not(name and port and host and staker and bootstrap_host and bootstrap_port):
            return jsonify({"error": "Missing fields"}, 409)

        if peer_instance:
            return jsonify({"error": "One peer is already running. Stop it to run another one"}, 409)
        
        staker_bool=p2p.strtobool(staker)
        peer_instance = p2p.Peer(host, port, name, staker_bool, persistent_load, persistent_save)
        peer_instance.connect_to_blockchain(bootstrap_host, bootstrap_port)
        set_consensus('pow')

        await asyncio.sleep(2)
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

async def stake():
    global peer_instance
    if not peer_instance:
        return jsonify({"success":False, "error": "No node is running"}, 409)

    if(not request.is_json):
        return jsonify({"success":False, "error": "Request must be JSON"})
    
    if(not peer_instance.staker):
        return jsonify({"success":False, "error": "Node is not a staker"})
    
    currTime=datetime.now()
    time_since=currTime-peer_instance.last_epoch_end_ts
    if(peer_instance.staked_amt>0):
        return jsonify({"success":False, "error": "Can't sent multiple stakes in one epoch"})
        
    if(time_since>timedelta(seconds=EPOCH_TIME*5/6)):
        if(time_since>timedelta(seconds=EPOCH_TIME*7/6)): 
            # we reset last epoch end time because we missed its end
            peer_instance.last_epoch_end_ts=datetime.now()
            peer_instance.staked_amt=0
            peer_instance.current_stakers.clear()
            peer_instance.current_stakes.clear()
            time_since = timedelta(seconds=0)
        
        else:
            return jsonify({"success":False, "error": f"Stake registration period closed, try again in the next epoch, time till next epoch : {EPOCH_TIME-time_since.seconds}"})

    data=request.get_json()
    amount=data.get('amount')

    if(not amount):
        return jsonify({"success":False, "error": "Bad Request, amount not specified"})

    try:
        amount = float(amount)
    except ValueError:
        return jsonify({"success":False, "error": "Amount must be a number"})
        
    if amount < 0:
        return jsonify({"success":False, "error": "Amount must be a positive value"})

    bal=peer_instance.chain.calc_balance(peer_instance.wallet.public_key_pem, peer_instance.mem_pool)
    if amount > bal:
        return jsonify({"success":False, "error": f"Insufficient Account Balance {amount}>{bal}"})
    
    await peer_instance.send_stake_announcements(amount)

    peer_instance.staked_amt=amount
    time_left=EPOCH_TIME-time_since.seconds
    asyncio.create_task(peer_instance.create_blocks(time_left))
    if(time_left<0):
        return jsonify({"success":False, "error": f"Please wait till the next epoch starts"})
    return jsonify({"success":True, "message": f"Creating block in {time_left} seconds"})


# current stakes, time since last epoch

def account_balance():
    global peer_instance
    if not peer_instance:
        return jsonify({"success":False, "error": "No node is running"}, 409)
    
    if not peer_instance.chain:
        return jsonify({"success":False, "error": "Chain hasn't been initialized"}, 409)
    
    try:
        print()
        amt=peer_instance..get_account_balance(peer_instance.wallet.public_key_pem, list(peer_instance.mem_pool))
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

        stakes_dict_list:List[Dict]=[]
        for stake in block.stakers:
            stake_dict=stake.to_dict()
            if(stake.sign):
                stake_dict["sign"]=base64.b64encode(stake.sign).decode()
            stakes_dict_list.append(stake_dict)
        
        if(block.transactions[0].sender=="Genesis"):
            chain_list.append({
                "id": block.id,
                "prevHash": block.prevHash,
                "transactions": blockchain_structures.txs_to_json_digestable_form(block.transactions),
                "ts": block.ts,
                "hash": block.hash,
                "miner": block.creator,
                "staked_amt":block.staked_amt,
                "files": file_list,
            })
        else:
            chain_list.append({
                "id": block.id,
                "prevHash": block.prevHash,
                "transactions": blockchain_structures.txs_to_json_digestable_form(block.transactions),
                "ts": block.ts,
                "hash": block.hash,
                "miner": block.creator,
                "staked_amt":block.staked_amt,
                "files": file_list,
                "stakes":stakes_dict_list,
                "vrf_proof":base64.b64encode(block.vrf_proof).decode(),
                "seed":block.seed
            })
    return jsonify({"success":True, "message":"succesful request", "chain": chain_list})

def current_stakes():
    global peer_instance
    current_stakes_list=[]
    for stake in list(peer_instance.current_stakes):
        entry=stake.to_dict()
        pubKey=stake.staker
        name='?'
        if pubKey==peer_instance.wallet.public_key_pem:
            name=peer_instance.name
        else:
            for nm, pk in peer_instance.name_to_public_key_dict.items():
                if pk == pubKey:
                    name=nm
        entry['name']=name
        current_stakes_list.append(entry)
    
    return jsonify({"success":True, "current_stakes": current_stakes_list})


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
