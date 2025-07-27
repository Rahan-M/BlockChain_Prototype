from flask import request, jsonify, Response
import json, asyncio, websockets
from collections import OrderedDict
from blockchain.pow import p2p, blockchain_structures
from ecdsa import VerifyingKey, MalformedPointError, curves
from ..app import set_consensus
import sys, traceback

peer_instance:p2p.Peer=None

async def start_new_blockchain():
    global peer_instance
    if request.is_json:
        data = request.get_json()
        name = data.get('name')
        port = int(data.get('port'))
        host = data.get('host')
        miner = data.get('miner')

        if peer_instance:
            return jsonify({"error": f"One peer is already running. Stop it to run another one"}, 409)
        
        if not(name and port and host and miner):
            return jsonify({"error": "Missing fields"}, 409)

        set_consensus('pow')
        miner_bool=p2p.strtobool(miner)
        # thread=threading.Thread(target=_start_peer_in_background,args=(host, port, name, miner_bool))
        # thread.daemon=True
        # thread.start()
        peer_instance = p2p.Peer(host, port, name, miner_bool)
        try:
            peer_instance.server=await websockets.serve(peer_instance.handle_connections, peer_instance.host, peer_instance.port)
            asyncio.create_task(peer_instance.server.wait_closed())
        except: # Catches all BaseException descendants
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print(f"An unexpected error occurred!")
            print(f"Type: {exc_type.__name__}")
            print(f"Value: {exc_value}")
            print(f"Traceback object: {exc_traceback}")
            # You can also use traceback.print_exc() for a more standard traceback output
            import traceback
            traceback.print_exc()
        
        peer_instance.chain=blockchain_structures.Chain(publicKey=peer_instance.wallet.public_key_pem)
        peer_instance.keepalive_task = asyncio.get_event_loop().create_task(
            peer_instance.run_forever()
        )

        peer_instance.init_repo()
        peer_instance.configure_ports()

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
        bootstrap_port = int(data.get('bootstrap_port'))
        bootstrap_host = data.get('bootstrap_host')

        if not(name and port and host and miner and bootstrap_host and bootstrap_port):
            return jsonify({"error": "Missing fields"}, 409)

        if peer_instance:
            return jsonify({"error": "One peer is already running. Stop it to run another one"}, 409)
        
        miner_bool=p2p.strtobool(miner)
        peer_instance = p2p.Peer(host, port, name, miner_bool)
        set_consensus('pow')
        try:
            peer_instance.server=await websockets.serve(peer_instance.handle_connections, peer_instance.host, peer_instance.port)
            asyncio.create_task(peer_instance.server.wait_closed())
            normalized_bootstrap_host, normalized_bootstrap_port = p2p.normalize_endpoint((bootstrap_host, bootstrap_port))
            asyncio.create_task(peer_instance.connect_to_peer(normalized_bootstrap_host, normalized_bootstrap_port))
        except: # Catches all BaseException descendants
            import sys
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print(f"An unexpected error occurred!")
            print(f"Type: {exc_type.__name__}")
            print(f"Value: {exc_value}")
            print(f"Traceback object: {exc_traceback}")
            # You can also use traceback.print_exc() for a more standard traceback output
            traceback.print_exc()
        

        peer_instance.consensus_task=asyncio.create_task(peer_instance.find_longest_chain())
        peer_instance.disc_task=asyncio.create_task(peer_instance.discover_peers())

        if peer_instance.miner:
            peer_instance.mine_task=asyncio.create_task(peer_instance.mine_blocks())

        peer_instance.init_repo()
        peer_instance.configure_ports()
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
    if(not request.is_json):
        return jsonify({"success":False, "error": "Request must be JSON"})

    data=request.get_json()
    public_key=data.get('public_key')
    amt=data.get('amt')

    if(not (public_key and amt)):
        return jsonify({"success":False, "error": "Public Key or Amount Not Found"})
    
    curve=curves.SECP256k1
    
    try:
        vk=VerifyingKey.from_pem(public_key)
        if(vk.curve!=curve):
            return jsonify({"success":False, "error": "Invalid Public Key"}, 409)
    
    except (MalformedPointError, ValueError, Exception) as e:
        return jsonify({"success":False, "error": "Invalid Public Key"}, 409)


    await peer_instance.create_and_broadcast_tx(public_key, amt)
    return jsonify({"success":True, "message": "Transaction Added"})
    

def account_balance():
    global peer_instance
    if not peer_instance:
        return jsonify({"success":False, "error": "No node is running"}, 409)
    
    if not peer_instance.chain:
        return jsonify({"success":False, "error": "Chain hasn't been initialized"}, 409)
    
    try:
        print()
        amt=peer_instance.chain.calc_balance(peer_instance.wallet.public_key_pem, list(peer_instance.mem_pool))
        return jsonify({"success":True, "message":"succesful request", "account_balance": amt})
    except:
        return jsonify({"success":False, "error": "error while fetching account balance"}, 409)



def get_status():
    global peer_instance
    amt=peer_instance.chain.calc_balance(peer_instance.wallet.public_key_pem, list(peer_instance.mem_pool))

    return Response(
        json.dumps(OrderedDict([
            ("success", True),
            ("name", peer_instance.name),
            ("host", peer_instance.host),
            ("port", peer_instance.port),
            ("account_balance", amt),
            ("public_key",peer_instance.wallet.public_key_pem),
            ("private_key",peer_instance.wallet.private_key_pem)
        ])),
        mimetype='application/json'
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
