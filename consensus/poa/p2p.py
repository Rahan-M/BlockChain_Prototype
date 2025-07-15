import asyncio, websockets
import argparse, json, uuid, base64
from typing import Set, Dict, List, Tuple
import copy
import threading
import socket
from consensus.poa.blochain_structures import Transaction, Block, Wallet, Chain, isvalidChain
from ipfs.ipfs import addToIpfs, download_ipfs_file_subprocess
from smart_contract.contracts_db import SmartContractDatabase
from smart_contract.secure_executor import SecureContractExecutor
from storage.storage_manager import save_node_id, load_node_id, save_key, load_key, save_chain, load_chain, save_peers, load_peers
from consensus.poa.flask_app import create_flask_app, run_flask_app
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
import binascii
import os
import tempfile
import subprocess
import hashlib
import ast
from pathlib import Path

MAX_CONNECTIONS = 8
GAS_PRICE = 0.001 # coin per gas unit
BASE_DEPLOY_COST = 5

def get_random_element(s):
    """
        Return a random element from a set
    """
    import random
    return random.choice(list(s)) if s else None

def normalize_endpoint(ep):
    """
        Return host resolved into ipv4 address and port converted into int datatype - maintains consistency in the code
    """
    host, port = ep
    return (socket.gethostbyname(host), int(port))

def get_contract_code_from_notepad():
    # Create a temporary file with a .py extension
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode='w+', encoding='utf-8') as tmp_file:
        temp_filename = tmp_file.name
        tmp_file.write("# Write your smart contract function here.\n")
        tmp_file.write("def contract_logic(parameter1, parameter2, parameter3, state):\n")
        tmp_file.write("    # your code here\n")
        tmp_file.write("    return state, 'some message'\n")
    
    # Open it in Notepad (waits until closed)
    subprocess.call(["notepad.exe", temp_filename])

    # Read the edited code
    with open(temp_filename, 'r', encoding='utf-8') as f:
        contract_code = f.read()

    # Optional: remove the temp file
    os.remove(temp_filename)

    return contract_code

class Peer:
    def __init__(self, host, port, name, activate_disk_load, activate_disk_save):
        self.host = host
        self.port = port
        self.name = name

        self.activate_disk_save = activate_disk_save

        self.ipfs_port = port + 50  # API port
        self.gateway_port = port + 81  # Gateway port
        self.swarm_tcp = port + 2
        self.swarm_udp = port + 3
        self.repo_path = Path.home() / f".ipfs_{port}"
        self.env = os.environ.copy()
        self.env["IPFS_PATH"] = str(self.repo_path)

        self.miner = False
        self.miner_task = None
        self.round = 0
        self.round_task = None

        self.admin_id = None

        if activate_disk_load == "y":
            self.load_node_id_from_disk()
        else:
            self.node_id = None
        if not self.node_id:
            self.node_id = str(uuid.uuid4())
            if self.activate_disk_save == "y":
                self.save_node_id_to_disk()

        self.miners: List[list]= list() # List of [miners_list, activation_block]

        self.server_connections :Set[websockets.WebSocketServerProtocol]=set() # For inbound peers ie websockets that connect to us and treat us as the server
        self.client_connections :Set[websockets.WebSocketServerProtocol]=set() # For outbound peers ie websockets we initiated, we are the clients

        self.outbound_peers: Set[tuple]=set()
        # The peers to which we currently maintain a outbound connection

        self.seen_message_ids: Set[str]= set()
        # Used to remove duplicate messages, messages that return to us after a round of broadcasting

        if activate_disk_load == "y":
            self.load_known_peers_from_disk()
        else:
            self.known_peers = None
        if not self.known_peers:
            self.known_peers: Dict[Tuple[str, int], Tuple[str, str, str]]={} # (host, port):(name, public key, node id)
        """
            We store all the peers we know here, we compare this with outbound peers in dicover_peers
            to find to which nodes we have not yet made a connection
        """
        

        self.got_pong: Dict[websockets.WebSocketServerProtocol, bool]={}
        """
            We set the value of each websocket in this dictionary false before sending ping
            If we get a pong from a particular websocekt we assign it True.
            We remove all websockets that don't send a pong in time. 
        """

        self.have_sent_peer_info: Dict[websockets.WebSocketServerProtocol, bool]={}
        """
            When we form an outbound connection, on receiving the first pong after our first ping
            we send them our peer_info, but we don't want to keep making the elaborate handshake
            so after the first time of getting pong we don't send them our peer info
            I'll explain the handshake in README.md
        """

        self.mem_pool: List[Transaction]=list()
        self.file_hashes: Dict[str, str]={}
        self.file_hashes_lock=asyncio.Lock()

        self.name_to_public_key_dict: Dict[str, str]={}
        self.node_id_to_name_dict: Dict[str, str]={}
        self.name_to_node_id_dict: Dict[str, str]={}
        
        if activate_disk_load == "y":
            self.load_key_from_disk()
        else:
            self.wallet = None
        if not self.wallet:
            self.wallet=Wallet()
            if self.activate_disk_save == "y":
                self.save_key_to_disk()

        if activate_disk_load == "y":
            self.load_chain_from_disk() # If no chain data stored, self.chain will be assigned to None
        else:
            self.chain = None

        self.contractsDB = SmartContractDatabase()

        self.mem_pool_condition=asyncio.Condition() 
        """
            Any block under this condition must acquire lock before moving on so we don't need to use both at the same time
            A condition is a synchronous primitive with an inbuilt lock
            This means that while a block of code starting with
            async with self.mem_pool_condition is executed only if
            there is no other such block currently being executed
        """

        self.daemon_process=None

    def save_node_id_to_disk(self):
        node_id = self.node_id
        save_node_id(node_id)

    def load_node_id_from_disk(self):
        node_id = load_node_id()
        if not node_id:
            self.node_id = None
            return
        self.node_id = node_id

    def save_key_to_disk(self):
        key = self.wallet.private_key_pem
        save_key(key)

    def load_key_from_disk(self):
        key = load_key()
        if not key:
            self.wallet = None
            return
        self.wallet = Wallet(key)

    def load_chain_from_disk(self):
        block_dict_list = load_chain()
        if not block_dict_list:
            self.chain = None
            return
        block_list: List[Block]=[]

        for block_dict in block_dict_list:
            block=self.block_dict_to_block(block_dict)
            block_list.append(block)

        self.chain=Chain(blockList=block_list)

    def save_chain_to_disk(self):
        chain = Chain.instance.to_block_dict_list()
        save_chain(chain)

    def save_known_peers_to_disk(self):
        content = {}
        for key, value in self.known_peers.items():
            content[json.dumps(key)] = list(value)
        save_peers(content)

    def load_known_peers_from_disk(self):
        content = load_peers()
        if not content:
            self.known_peers = None
            return
        self.known_peers = {}
        for key, value in content.items():
            self.known_peers[tuple(ast.literal_eval(key))] = tuple(value)

    def get_peer_info_message(self):
        """
            Function made to send the peer (self) info
        """
        pkt={
            "type":"peer_info",
            "id":str(uuid.uuid4()),
            "data":{
                "host":self.host,
                "port":self.port,
                "name":self.name,
                "public_key":self.wallet.public_key,
                "node_id":self.node_id
                }
        }

        self.seen_message_ids.add(pkt["id"])

        return pkt

    def get_known_peers_message(self):
        """
            Function for sending known_peers
            (information regarding all the peers we know)
        """
        peers=[{"host":h, "port":p, "name":n, "public_key":s, "node_id":i}
               for (h, p), (n, s, i) in self.known_peers.items()]
        peers.append({"host":self.host, "port":self.port, "name":self.name, "public_key":self.wallet.public_key, "node_id":self.node_id})
        pkt={
            "type":"known_peers",
            "id":str(uuid.uuid4()),
            "peers":peers
        }

        self.seen_message_ids.add(pkt["id"])

        return pkt

    async def broadcast_miners_list(self, miners_list, activation_block):
        pkt={
            "type":"miners_list_update",
            "id":str(uuid.uuid4()),
            "miners_list": miners_list,
            "activation_block": activation_block,
        }
        message = json.dumps(pkt, sort_keys=True).encode()
        signature = self.wallet.private_key.sign(
            message,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        pkt["signature"] = signature.hex()
        self.seen_message_ids.add(pkt["id"])
        await self.broadcast_message(pkt)

    def block_dict_to_block(self, block_dict):    
        """
            This function creates a block out of the information
            stored inside block_dict
            We sent a receive blocks as a dictionary
            block["trasnsactions"] is a list of dictionaries that
            represent transactions
        """

        new_block_id=block_dict["id"]
        new_block_prevHash=block_dict["prevHash"]
        new_block_ts=block_dict["ts"]
        new_block_miner_node_id = block_dict["miner_node_id"]
        new_block_miner_public_key = block_dict["miner_public_key"]
        new_block_miners_list = block_dict["miners_list"]
        new_block_signature = block_dict["signature"]

        transactions=[]
        for transaction_dict in block_dict["transactions"]:
            transaction=Transaction(transaction_dict["payload"], transaction_dict["sender"], transaction_dict["receiver"], transaction_dict["id"], transaction_dict["timestamp"])
            if(transaction.sender!="Genesis"):
                transaction.sign=base64.b64decode(transaction_dict["sign"])
            transactions.append(transaction)
        
        newBlock=Block(new_block_prevHash, transactions, new_block_ts, new_block_id)
        newBlock.miner_node_id = new_block_miner_node_id
        newBlock.miner_public_key = new_block_miner_public_key
        newBlock.miners_list = new_block_miners_list
        newBlock.files=block_dict["files"]
        newBlock.signature = new_block_signature
        return newBlock

    def get_public_key_by_node_id(self, target_node_id):
        for (host, port), (name, public_key, node_id) in self.known_peers.items():
            if node_id == target_node_id:
                return public_key
        return None

    def get_current_miners_list(self):
        miners_list = None
        if self.miners and len(Chain.instance.chain) == self.miners[0][1]:
            miners_list = self.miners[0][0]
            for i in range(1, len(self.miners)):
                if self.miners[i][1] == len(Chain.instance.chain):
                    miners_list = self.miners[i][0]
                else:
                    break
        else:
            miners_list = Chain.instance.chain[-1].miners_list
        return miners_list

    def discard_server_connection_details(self, websocket):
        self.server_connections.discard(websocket)

    def discard_client_connection_details(self, websocket):
        normalized_endpoint = normalize_endpoint((websocket.remote_address[0], websocket.remote_address[1]))
        self.client_connections.discard(websocket)
        self.outbound_peers.discard(normalized_endpoint)
        self.got_pong.pop(websocket, None)
        self.have_sent_peer_info.pop(websocket, None)

    async def update_role(self, is_miner_now): 
        if is_miner_now and not self.miner:
            # Become miner
            self.miner = True
            self.miner_task = asyncio.create_task(self.mine_blocks())

        elif not is_miner_now and self.miner:
            # Stop mining
            self.miner = False
            if self.miner_task:
                try:
                    self.miner_task.cancel()
                    await self.miner_task
                except asyncio.CancelledError:
                    pass

    async def round_calculator(self):
        self.round = 0
        try:
            while True:
                for _ in range(2):
                    await asyncio.sleep(5)
                if len(self.mem_pool) > 0:
                    for _ in range(16):
                        await asyncio.sleep(5)
                    print("Shifting miner...")
                    self.round = self.round + 1
                    print("Miner shifted")
        except asyncio.CancelledError:
            print("Round calculator task stopped cleanly")

    def valid_deploy_transaction(self, payload):
        contract_code = payload[0]
        gas_used = len(contract_code)//10 + BASE_DEPLOY_COST
        amount = gas_used * GAS_PRICE
        if amount != payload[-1]:
            return False
        return True

    def valid_invoke_transaction(self, payload):
        contract_id = payload[0]
        func_name = payload[1]
        args = payload[2]
        response = self.run_contract([contract_id, func_name, args])
        if(response["error"] != None):
            return False
        state = response["state"]
        gas_used = response["gas_used"]
        amount = gas_used * GAS_PRICE
        if state != payload[3]:
            return False
        if amount != payload[-1]:
            return False
        return True

    async def handle_messages(self, websocket, msg):
        """
            This is a function to handle messages as the name suggests
        """
        """
            It faciliates the handshake between client and server. 
            It also accepts transactions, blocks and chains in the format
            in which we send them. Then this function recreates these and
            performs the necessary operations
        """
        # Read the handshake protocol within readme to understand the flow of messages

        t=msg.get("type")
        id=msg.get("id")
        # Every message has a type and an id

        if not t or not id:
            return
        if id in self.seen_message_ids:
            return
        
        self.seen_message_ids.add(id)

        if t=="miners_list_update":
            try:
                public_key = serialization.load_pem_public_key(
                    self.get_public_key_by_node_id(self.admin_id).encode(),
                    backend=default_backend()
                )

                message = json.dumps({
                    "type":"miners_list_update",
                    "id":msg["id"],
                    "miners_list":msg["miners_list"],
                    "activation_block":msg["activation_block"],
                }, sort_keys=True).encode()

                signature = binascii.unhexlify(msg["signature"])

                public_key.verify(
                    signature,
                    message,
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
            except Exception as e:
                print(f"Invalid miners list update signature: {e}")
                return
            self.miners.append([msg["miners_list"], msg["activation_block"]])
            await self.broadcast_message(msg)

        elif t=="ping":

            pkt={
                "type":"pong",
                "id":str(uuid.uuid4())
                }
            
            self.seen_message_ids.add(pkt["id"])

            await self.send_message(websocket, pkt, False)

        elif t=="pong":
            # print("Received Pong")
            self.got_pong[websocket]=True
            if not self.have_sent_peer_info.get(websocket, True):
                message = self.get_peer_info_message()
                await self.send_message(websocket, message, True)
                self.have_sent_peer_info[websocket]=True
            # print(f"[Sent peer]")

        elif t =='peer_info' or t == "add_peer":
            # print("Received Peer Info")
            data=msg["data"]
            normalized_self=normalize_endpoint((self.host, self.port))
            normalized_endpoint = normalize_endpoint((data["host"], data["port"]))
            if normalized_endpoint not in self.known_peers and normalized_endpoint!=normalized_self :
                self.known_peers[normalized_endpoint]=(data["name"], data["public_key"], data["node_id"])
                if self.activate_disk_save == "y":
                    self.save_known_peers_to_disk()
                self.name_to_public_key_dict[data["name"].lower()]=data["public_key"]
                self.node_id_to_name_dict[data["node_id"]]=data["name"].lower()
                self.name_to_node_id_dict[data["name"].lower()]=data["node_id"]
                print(f"Registered peer {data["name"]} {data["host"]}:{data["port"]}")
                if t == 'add_peer':
                    await self.broadcast_message(msg)
                message = self.get_known_peers_message()
                await self.send_message(websocket, message, False)

        elif t=="known_peers":
            # print("Received Known Peers")
            peers=msg["peers"]
            new_peer_found = False
            for peer in peers:
                normalized_self=normalize_endpoint((self.host, self.port))
                normalized_endpoint = normalize_endpoint((peer["host"], peer["port"]))
                if normalized_endpoint not in self.known_peers and normalized_endpoint!=normalized_self:
                    print(f"Discovered peer {peer["name"]} at {peer["host"]}:{peer["port"]}")
                    new_peer_found = True
                    self.known_peers[normalized_endpoint]=(peer["name"], peer["public_key"], peer["node_id"])
                    self.name_to_public_key_dict[peer["name"].lower()]=peer["public_key"]
                    self.node_id_to_name_dict[peer["node_id"]]=peer["name"].lower()
                    self.name_to_node_id_dict[peer["name"].lower()]=peer["node_id"]
            if new_peer_found:
                if self.activate_disk_save == "y":
                    self.save_known_peers_to_disk()
            pkt={
                "type":"network_details_request",
                "id":str(uuid.uuid4())
            }
            await self.send_message(websocket, pkt, True)

        elif t=="file":
            cid=msg["cid"]
            desc=msg["desc"]
            async with self.file_hashes_lock:
                self.file_hashes[cid]=desc
                
            await self.broadcast_message(msg)

        elif t=="network_details_request":
            pkt={
                "type": "network_details",
                "id":str(uuid.uuid4()),
                "admin": self.admin_id,
                "miners": self.miners
            }
            await self.send_message(websocket, pkt, False)

        elif t=="network_details":
            self.admin_id = msg["admin"]
            self.miners = msg["miners"]
            pkt={
                "type":"chain_request",
                "id":str(uuid.uuid4())
            }
            await self.send_message(websocket, pkt, True)

        elif t=="new_tx":
            tx_str=msg["transaction"]
            tx=json.loads(tx_str)
            transaction: Transaction=Transaction(tx['payload'], tx['sender'], tx['receiver'], tx['id'], tx['timestamp'])
            if Chain.instance.transaction_exists_in_chain(transaction):
                print(f"{self.name} Transaction already exists in chain")
                return
            
            sign_bytes=base64.b64decode(msg["sign"])
            #b64decode turns bytes into a string

            if transaction.receiver == "deploy":
                if not self.valid_deploy_transaction(transaction.payload):
                    return
            if transaction.receiver == "invoke":
                if not self.valid_invoke_transaction(transaction.payload):
                    return

            amount = 0
            if transaction.receiver == "deploy" or transaction.receiver == "invoke":
                amount = transaction.payload[-1]
            else:
                amount = transaction.payload
            if(amount>Chain.instance.calc_balance(transaction.sender, self.mem_pool)):
                print("\nAttempt to spend more than one has, Invalid transaction\n")
                return

            try:
                public_key=serialization.load_pem_public_key(tx['sender'].encode())
                public_key.verify(
                    sign_bytes,
                    tx_str.encode(),
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
            except:
                print("Invalid Signature")
                return
            
            transaction.sign=sign_bytes
            
            print("\nValid Transaction")
            print(f"\n{msg["type"]}: {msg["transaction"]}")
            print("\n")

            async with self.mem_pool_condition:
                self.mem_pool.append(transaction)
                # self.mem_pool_condition.notify_all()
            await self.broadcast_message(msg)

        elif t=="new_block":
            new_block_dict=msg["block"]
            newBlock=self.block_dict_to_block(new_block_dict)
            miners_list = self.get_current_miners_list()
            reqd_miner_node_id = miners_list[(len(Chain.instance.chain) + self.round) % len(miners_list)]
            reqd_miner_pulic_key = self.get_public_key_by_node_id(reqd_miner_node_id)

            if not Chain.instance.isValidBlock(newBlock, reqd_miner_node_id, reqd_miner_pulic_key):
                print("\nInvalid Block\n")
                return
            
            for transaction in newBlock.transactions:
                if transaction.receiver == "invoke":
                    if not self.valid_invoke_transaction(transaction.payload):
                        return
                if transaction.receiver == "deploy":
                    if not self.valid_deploy_transaction(transaction.payload):
                        return
                    
            Chain.instance.chain.append(newBlock)
            print("\n\n Block Appended \n\n")

            for transaction in newBlock.transactions:
                if transaction.receiver == "deploy":
                    self.deploy_contract(transaction)
            
            async with self.mem_pool_condition:
                for transaction in self.mem_pool:
                    if newBlock.transaction_exists_in_block(transaction):
                        self.mem_pool.remove(transaction)
                        
            async with self.file_hashes_lock:
                for hash in list(self.file_hashes.keys()):
                    if newBlock.cid_exists_in_block(hash):
                        self.file_hashes.pop(hash, None)

            await self.broadcast_message(msg)
            self.round_task.cancel()
            await self.round_task
            self.round_task = asyncio.create_task(self.round_calculator())

            while self.miners:
                if self.miners[0][1] < len(Chain.instance.chain):
                    self.miners.pop(0)
                else:
                    break

            new_miners_list = self.get_current_miners_list()
            if self.node_id in new_miners_list:
                await self.update_role(True)
            else:
                await self.update_role(False)
            if self.activate_disk_save == "y":
                self.save_chain_to_disk()

        elif t=="chain_request":
            if not self.chain:
                return
            pkt={
                "type":"chain",
                "id":str(uuid.uuid4()),
                "chain":Chain.instance.to_block_dict_list()
            }
            await self.send_message(websocket, pkt, False)

        elif t=="chain":
            print("Received a Chain")
            block_dict_list=msg["chain"]
            block_list: List[Block]=[]

            for block_dict in block_dict_list:
                block=self.block_dict_to_block(block_dict)
                block_list.append(block)

            if not isvalidChain(block_list):
                print("\nInvalid Chain\n")
                return
            #If chain doesn't already exist we assign this as the chain
            if not self.chain:
                self.chain=Chain(blockList=block_list)
                if self.activate_disk_save == "y":
                    self.save_chain_to_disk()

            elif(len(Chain.instance.chain)<len(block_list)):
                Chain.instance.rewrite(block_list)
                print("\nCurrent chain replaced by longer chain")
                if self.activate_disk_save == "y":
                    self.save_chain_to_disk()
            
            else:
                print("\nCurrent Chain Longer than received chain")
                return
            async with self.mem_pool_condition:
                for transaction in list(self.mem_pool):
                    if Chain.instance.transaction_exists_in_chain(transaction):
                        self.mem_pool.discard(transaction)

            async with self.file_hashes_lock:
                for hash in list(self.file_hashes.keys()):
                    if(Chain.instance.cid_exists_in_chain(hash)):
                        self.file_hashes.pop(hash, None)

    async def handle_connections(self, websocket):
        """
            We handle our server connections from here.
            Primary job is to simply read messages and send it to 
            handle_messages function
        """
        peer_addr=(websocket.remote_address[0], websocket.remote_address[1])
        self.server_connections.add(websocket)

        print(f"Inbound Connection from {peer_addr[0]}:{peer_addr[1]}")
        
        try:
            async for raw in websocket:
                msg=json.loads(raw)
                await self.handle_messages(websocket, msg)

        except websockets.exceptions.ConnectionClosed:
            print(f"Inbound Connection Closed: {peer_addr}")

        finally:
            self.discard_server_connection_details(websocket)
            await websocket.close()
            await websocket.wait_closed()

    async def send_message(self, websocket, message, client_connection):
        try:
            await websocket.send(json.dumps(message))
        except Exception as e:
            print(f"Unexpected error during WebSocket send: {e}")
            if client_connection:
                self.discard_client_connection_details(websocket)
            else:
                self.discard_server_connection_details(websocket)
            await websocket.close()
            await websocket.wait_closed()

    async def broadcast_message(self, pkt):
        # For broadcasting messages to all the connections we have

        targets=self.server_connections | self.client_connections
        for ws in targets:
            if ws in self.server_connections:
                await self.send_message(ws, pkt, False)
            else:
                await self.send_message(ws, pkt, True)

    async def create_and_broadcast_tx(self, receiver_public_key, payload):
        """
            Function to create and broadcast transactions
        """
        transaction=Transaction(payload, self.wallet.public_key, receiver_public_key)
        transaction_str=str(transaction)
        
        signature=self.wallet.private_key.sign(
            transaction_str.encode(),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        signature_b64=base64.b64encode(signature).decode()
        # b64encode returns bytes, Decode converts bytes to string
        
        pkt={
            "type":"new_tx",
            "id":str(uuid.uuid4()),
            "transaction":transaction_str,
            "sign":signature_b64,
            "sender_pem":self.wallet.public_key # Already available as a pem string as defined in constructor
        }
        
        self.seen_message_ids.add(pkt["id"])
        if Chain.instance.transaction_exists_in_chain(transaction):
            return
        
        transaction.sign=signature
        async with self.mem_pool_condition:
                self.mem_pool.append(transaction)
                # self.mem_pool_condition.notify_all()

        print("Transaction Created", transaction)
        print("\n")
        await self.broadcast_message(pkt)

    def get_contract_state(self, contract_id):
        for block in reversed(Chain.instance.chain):
            for transaction in reversed(block.transactions):
                if transaction.receiver == "invoke" and transaction.payload[0] == contract_id:
                    return transaction.payload[3]
        return {}

    async def user_input_handler(self):
        """
            A function to constantly take input from the user 
            about whom to send and how much
        """
        while True:
            print("Block Chain Menu\n***************")
            menu = "1) Add Transaction\n2) View balance\n3) Print Chain\n4) Print Pending Transactions\n5) Send Files\n6) Download Files\n"
            if self.node_id == self.admin_id:
                menu = menu + "7) View Miners\n8) Add Miner\n9) Remove Miner\n"
            menu = menu + "0) Quit"
            print(menu)

            ch= await asyncio._get_running_loop().run_in_executor(
                None, input, "Enter Your Choice: "
            )
            try:
                ch=int(ch)
            except:
                print("\nPlease enter a valid number!!!\n")
            if ch==1:
                rec = await asyncio._get_running_loop().run_in_executor(
                    None, input, "\nEnter Receiver's Name: "
                )

                if rec == "deploy":
                    contract_code = get_contract_code_from_notepad()
                    if not contract_code:
                        print("Contract code field is empty")
                        continue
                    gas_used = len(contract_code)//10 + BASE_DEPLOY_COST
                    amount = gas_used * GAS_PRICE
                    payload = [contract_code, amount]

                    if amount<=Chain.instance.calc_balance(self.wallet.public_key, self.mem_pool):
                        await self.create_and_broadcast_tx(rec, payload)
                    else:
                        print("Insufficient Account Balance")
                elif rec == "invoke":
                    contract_id = await asyncio._get_running_loop().run_in_executor(
                        None, input, "\nEnter Contract Id: "
                    )
                    if contract_id not in self.contractsDB.contracts:
                        print("No such contract found...")
                        continue

                    func_name = await asyncio._get_running_loop().run_in_executor(
                        None, input, "\nEnter Function Name: "
                    )

                    args = []
                    loop = asyncio.get_running_loop()
                    arg_number = 1
                    while True:
                        arg = await loop.run_in_executor(None, input, f"Enter argument {arg_number} (or \\q to finish): ")
                        if arg.strip() == "\\q":
                            break
                        try:
                            parsed_arg = ast.literal_eval(arg)
                        except Exception:
                            parsed_arg = arg
                        args.append(parsed_arg)
                        arg_number += 1

                    response = self.run_contract([contract_id, func_name, args])
                    if(response["error"] != None):
                        print("Error: ", response["error"])
                        continue
                    state = response["state"]
                    gas_used = response["gas_used"]
                    amount = gas_used * GAS_PRICE

                    payload = [contract_id, func_name, args, state, amount]

                    if amount<=Chain.instance.calc_balance(self.wallet.public_key, self.mem_pool):
                        await self.create_and_broadcast_tx(rec, payload)
                    else:
                        print("Insufficient Account Balance")
                else:
                    amt= await asyncio._get_running_loop().run_in_executor(
                        None, input, "\nEnter Amount to send: "
                    )
                    receiver_public_key = self.name_to_public_key_dict.get(rec.lower().strip())
                    if(receiver_public_key==None):
                        print("No such person available in directory...")
                        continue
                    
                    try:
                        amt=float(amt)
                    except ValueError:
                        print("Amount must be a number")
                        continue

                    if amt<=Chain.instance.calc_balance(self.wallet.public_key, self.mem_pool):
                        await self.create_and_broadcast_tx(receiver_public_key, amt)
                    else:
                        print("Insufficient Account Balance")

            elif ch==2:
                print("Account Balance =",Chain.instance.calc_balance(self.wallet.public_key, self.mem_pool))
            elif ch==3:
                i=0
                # We print all the blocks
                for block in Chain.instance.chain:
                    print(f"block{i}: {block}\n")
                    i+=1            
            elif ch==4:
                i=0
                for transaction in self.mem_pool:
                    print(f"transaction{i}: {transaction}\n\n")
                    i+=1

            elif ch==5:
                desc= await asyncio._get_running_loop().run_in_executor(
                    None, input, "\nEnter description of file: "
                )
                path= await asyncio._get_running_loop().run_in_executor(
                    None, input, "\nEnter path of file: "
                )
                pkt= await self.uploadFile(desc, path)
                if(pkt):
                    await self.broadcast_message(pkt)

            elif ch==6:
                cid= await asyncio._get_running_loop().run_in_executor(
                    None, input, "\nEnter cid of file: "
                )
                path= await asyncio._get_running_loop().run_in_executor(
                    None, input, "\nEnter path to download the file: "
                )
                download_ipfs_file_subprocess(cid, path)

            elif ch==7:
                miner_names = list()
                for miner in Chain.instance.chain[-1].miners_list:
                    miner_names.append(self.node_id_to_name_dict[miner])
                print("Current miners")
                print(miner_names)
                for miner_item in self.miners:
                    miner_names.clear()
                    for miner in miner_item[0]:
                        miner_names.append(self.node_id_to_name_dict[miner])
                    print(f"Miners to be activated from block {miner_item[1]}")
                    print(miner_names)
            elif ch==8:
                miner_name = await asyncio._get_running_loop().run_in_executor(
                    None, input, "\nEnter Miner's Name: "
                )
                miner_node_id = None
                try:
                    miner_node_id = self.name_to_node_id_dict[miner_name.lower()]
                except Exception as e:
                    print(f"An error occured: {e}")
                    continue
                miners_list = None
                if self.miners:
                    miners_list = copy.deepcopy(self.miners[-1][0])
                else:
                    miners_list = copy.deepcopy(Chain.instance.chain[-1].miners_list)
                if miner_node_id not in miners_list:
                    miners_list.append(miner_node_id)
                    self.miners.append([miners_list, len(Chain.instance.chain) + 3])
                    await self.broadcast_miners_list(miners_list, len(Chain.instance.chain) + 3)
                else:
                    print(f"{miner_name} is already in miners list")
            elif ch==9:
                miner_name = await asyncio._get_running_loop().run_in_executor(
                    None, input, "\nEnter Miner's Name: "
                )
                miner_node_id = None
                try:
                    miner_node_id = self.name_to_node_id_dict[miner_name.lower()]
                except Exception as e:
                    print(f"An error occured: {e}")
                    continue
                miners_list = None
                if self.miners:
                    miners_list = copy.deepcopy(self.miners[-1][0])
                else:
                    miners_list = copy.deepcopy(Chain.instance.chain[-1].miners_list)
                if miner_node_id in miners_list:
                    miners_list.remove(miner_node_id)
                    self.miners.append([miners_list, len(Chain.instance.chain) + 3])
                    await self.broadcast_miners_list(miners_list, len(Chain.instance.chain) + 3)
                else:
                    print(f"{miner_name} is already not in miners list")
            elif ch==0:
                print("Quitting...")
                break

    async def connect_to_peer(self, host, port):
        """
            Function to form an outbound connection to the given host:port
            and handle messages that come form this connection
            Also initiates the handshake
        """

        endpoint=(host, port)
        if endpoint in self.outbound_peers or endpoint==(self.host, self.port):
            return

        uri=f"ws://{host}:{port}"
        
        websocket = None
        try:
            websocket=await websockets.connect(uri)
            self.client_connections.add(websocket)
            self.outbound_peers.add(endpoint)
            self.have_sent_peer_info[websocket]=False

            print(f"Outbound connection formed to {host}:{port}")

            # If connecting first time to the network, broadcasts node information to the entire network
            if Chain.instance == None:
                pkt={
                    "type":"add_peer",
                    "id":str(uuid.uuid4()),
                    "data":{
                        "host":self.host,
                        "port":self.port,
                        "name":self.name,
                        "public_key":self.wallet.public_key,
                        "node_id":self.node_id
                    }
                }

                self.seen_message_ids.add(pkt["id"])
                await self.send_message(websocket, pkt, True)
                
            ping={
                "type":"ping",
                "id":str(uuid.uuid4()),
            }
            self.seen_message_ids.add(ping["id"])
            await self.send_message(websocket, ping, True)

            async for raw in websocket:
                msg=json.loads(raw)
                await self.handle_messages(websocket, msg)
        except Exception as e:
            print(f"Failed to connect to {host}:{port} ::: {e}")
        finally:
            if not websocket:
                return
            self.discard_client_connection_details(websocket)
            await websocket.close()
            await websocket.wait_closed()

    async def discover_peers(self):
        """
            Maintains up to MAX_CONNECTIONS peers.
            Connects only to fill the pool if under MAX_CONNECTIONS.
        """

        while True:
            if len(self.outbound_peers) < MAX_CONNECTIONS:
                potential_peers = {
                    endpoint for endpoint in self.known_peers
                    if endpoint not in self.outbound_peers and endpoint != (self.host, self.port)
                }
                while len(self.outbound_peers) < MAX_CONNECTIONS and potential_peers:
                    new_peer = get_random_element(potential_peers)
                    potential_peers.discard(new_peer)
                    if new_peer:
                        asyncio.create_task(self.connect_to_peer(*new_peer))
                        await asyncio.sleep(1)
            for _ in range(6):
                    await asyncio.sleep(5)

    async def gossip_peer_sampler(self):
        """
            Every 60s, drops one existing peer and connects to one new peer.
        """
        while True:
            for _ in range(12):
                    await asyncio.sleep(5)
            if len(self.known_peers) <= len(self.outbound_peers) or len(self.outbound_peers) < MAX_CONNECTIONS:
                continue  # Nothing to swap

            # Disconnect one random client connection
            to_drop = get_random_element(self.client_connections)
            if to_drop:
                print(f"Gossip Sampling: Disconnecting {to_drop.remote_address}")
                self.client_connections.discard(to_drop)
                normalized_endpoint = normalize_endpoint((to_drop.remote_address[0], to_drop.remote_address[1]))
                self.outbound_peers.discard(normalized_endpoint)
                self.got_pong.pop(to_drop, None)
                self.have_sent_peer_info.pop(to_drop, None)
                await to_drop.close()
                await to_drop.wait_closed()

            # Connect to a new peer (not already connected)
            potential_peers = {
                endpoint for endpoint in self.known_peers
                if endpoint not in self.outbound_peers and endpoint != (self.host, self.port)
            }

            if potential_peers:
                new_peer = get_random_element(potential_peers)
                if new_peer:
                    print(f"Gossip Sampling: Connecting to new peer {new_peer}")
                    asyncio.create_task(self.connect_to_peer(*new_peer))

    async def uploadFile(self, desc: str, path:str):
        file_path=Path(path)
        if(not file_path.is_file()):
            print("\nFile doesn't exist\n")
            return

        if not self.daemon_process: 
            self.start_daemon()
        
        cid, name = await asyncio.to_thread(addToIpfs, path)
        if(not(cid and name)):
            return
        
        print(f"\nNew File Created : {cid}\n")
        pkt={
            "type":"file",
            "id":str(uuid.uuid4()),
            "desc":desc,
            "cid":cid
        }
        
        self.seen_message_ids.add(pkt["id"])
        async with self.file_hashes_lock:
            self.file_hashes[cid]=desc
        return pkt

    def init_repo(self):
        """
            Creates a ipfs repo of name ending in ipfs_port_no eg ipfs_5000 
        """
        if not self.repo_path.exists():
            subprocess.run(["ipfs", "init"], env=self.env, check=True)
            print("\nIPFS repo created\n")

    def configure_ports(self):
        subprocess.run(["ipfs", "config", "Addresses.API", f"/ip4/127.0.0.1/tcp/{self.ipfs_port}"], env=self.env, check=True)
        subprocess.run(["ipfs", "config", "Addresses.Gateway", f"/ip4/127.0.0.1/tcp/{self.gateway_port}"], env=self.env, check=True)
        subprocess.run([
            "ipfs", "config", "Addresses.Swarm", "--json",
            f'["/ip4/127.0.0.1/tcp/{self.swarm_tcp}", "/ip4/127.0.0.1/udp/{self.swarm_udp}/quic"]'
        ], env=self.env, check=True)
        print("\nConfigured Ports\n")

    def start_daemon(self):
        self.daemon_process= subprocess.Popen(["ipfs", "daemon"], env=self.env)
        print("\nIPFS Daemon Started\n")

    def stop_daemon(self):
        if self.daemon_process:
            self.daemon_process.terminate()
            self.daemon_process.wait()

    def sign_block(self, block: Block):
        message = block.get_message_to_sign()
        signature = self.wallet.private_key.sign(
            message,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        block.signature = signature.hex()  # Store as hex string for transport

    async def mine_blocks(self):
        try:
            while True:
                for _ in range(6):
                    await asyncio.sleep(5)
                miners_list = self.get_current_miners_list()
                reqd_miner_node_id = miners_list[(len(Chain.instance.chain) + self.round) % len(miners_list)]
                if self.node_id == reqd_miner_node_id:
                    if self.round != 0:
                        for _ in range(3):
                            await asyncio.sleep(5)
                    async with self.mem_pool_condition: # Works the same as lock
                        # await self.mem_pool_condition.wait_for(lambda: len(self.mem_pool) >= 3)
                        # We check the about condition in lambda every time we get notified after a new transaction has been added
                        if(len(self.mem_pool)>0):
                            transaction_list=[]
                            for transaction in self.mem_pool:
                                if Chain.instance.transaction_exists_in_chain(transaction):
                                    self.mem_pool.remove(transaction)
                                    continue
                                else:
                                    transaction_list.append(transaction)

                            if(len(transaction_list)>0):
                                print("Mining Started")
                                print("Mining...")
                                newBlock = Block(Chain.instance.lastBlock.hash, transaction_list)
                                newBlock.miner_node_id = self.node_id
                                newBlock.miner_public_key = self.wallet.public_key
                                newBlock.miners_list = miners_list
                                newBlock.files=self.file_hashes.copy()
                                self.sign_block(newBlock)

                                reqd_miner_pulic_key = self.wallet.public_key
                                if not Chain.instance.isValidBlock(newBlock, reqd_miner_node_id, reqd_miner_pulic_key):
                                    print("\nInvalid Block\n")
                                    return
                        
                                Chain.instance.chain.append(newBlock)
                                print("\nBlock Appended \n")

                                for transaction in newBlock.transactions:
                                    if transaction.receiver == "deploy":
                                        self.deploy_contract(transaction)

                                for transaction in self.mem_pool:
                                    if newBlock.transaction_exists_in_block(transaction):
                                        self.mem_pool.remove(transaction)

                                async with self.file_hashes_lock:
                                    for hash in list(self.file_hashes.keys()):
                                        if newBlock.cid_exists_in_block(hash):
                                            self.file_hashes.pop(hash, None)

                                pkt={
                                    "type":"new_block",
                                    "id":str(uuid.uuid4()),
                                    "block":newBlock.to_dict()
                                }

                                self.seen_message_ids.add(pkt["id"])
                                await self.broadcast_message(pkt)
                                self.round_task.cancel()
                                await self.round_task
                                self.round_task = asyncio.create_task(self.round_calculator())

                                while self.miners:
                                    if self.miners[0][1] < len(Chain.instance.chain):
                                        self.miners.pop(0)
                                    else:
                                        break

                                new_miners_list = self.get_current_miners_list()
                                if self.node_id in new_miners_list:
                                    await self.update_role(True)
                                else:
                                    await self.update_role(False)
                                if self.activate_disk_save == "y":
                                    self.save_chain_to_disk()

        except asyncio.CancelledError:
            print("Miner task stopped cleanly")
            raise

    async def find_longest_chain(self):
        """
            We routinely check every 30 seconds, every other chain and we replace
            ours with theirs if theirs is >= ours
        """
        while True:
            pkt={
                "type":"chain_request",
                "id":str(uuid.uuid4())
            }
            self.seen_message_ids.add(pkt["id"])
            await self.broadcast_message(pkt)
            print("\nSent out chain requests...")
            for _ in range(12):
                    await asyncio.sleep(5)

    def calculate_contract_id(self, sender, timestamp):
        data = f"{sender}:{timestamp}"
        hash_object = hashlib.sha256(data.encode('utf-8'))
        return hash_object.hexdigest()
        
    def deploy_contract(self, transaction):
        sender = transaction.sender
        timestamp = transaction.ts
        code = transaction.payload[0]
        contract_id = self.calculate_contract_id(sender, timestamp)
        self.contractsDB.store_contract(contract_id, code)
        print("Contract deployed with id: ", contract_id)

    def run_contract(self, payload):
        contract_id, func_name, args = payload[0], payload[1], payload[2]
        code = self.contractsDB.get_contract(contract_id)
        if code is None:
            raise Exception(f"Contract '{contract_id}' not found.")

        state = self.get_contract_state(contract_id)
        executor = SecureContractExecutor(code)
        response = executor.run(func_name, args, state)

        return response

    async def start(self, bootstrap_host=None, bootstrap_port=None):
        # We start the server
        await websockets.serve(self.handle_connections, self.host, self.port)
        # We await the setting up of the server and the handle connections funciton,
        # This returns a websocket server object eventually

        # If bootstrap node is given we connect to it and take its chain
        if bootstrap_host and bootstrap_port:
            normalized_bootstrap_host, normalized_bootstrap_port = normalize_endpoint((bootstrap_host, bootstrap_port))
            asyncio.create_task(self.connect_to_peer(normalized_bootstrap_host, normalized_bootstrap_port))
        else:
            self.chain=Chain(publicKey=self.wallet.public_key)
            Chain.instance.chain[0].miner_node_id = self.node_id
            Chain.instance.chain[0].miner_public_key = self.wallet.public_key
            Chain.instance.chain[0].miners_list = [self.node_id]
            self.sign_block(Chain.instance.chain[0])
            self.admin_id = self.node_id
            await self.update_role(True)

        # Create flask app
        flask_app = create_flask_app(self)
        flask_thread = threading.Thread(target=run_flask_app, args=(flask_app, self.port), daemon=True)
        flask_thread.start()
        inp_task=asyncio.create_task(self.user_input_handler())
        consensus_task=asyncio.create_task(self.find_longest_chain())
        disc_task=asyncio.create_task(self.discover_peers())
        sampler_task = asyncio.create_task(self.gossip_peer_sampler())
        self.round_task = asyncio.create_task(self.round_calculator())

        self.init_repo()
        self.configure_ports()

        await inp_task

        consensus_task.cancel()
        disc_task.cancel()
        sampler_task.cancel()
        self.round_task.cancel()

        if self.daemon_process:
            self.stop_daemon()

        await self.update_role(False)