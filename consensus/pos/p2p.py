import asyncio, websockets, traceback, hashlib
import argparse, json, uuid, base64
import threading, socket, os, subprocess
from datetime import datetime, timedelta
from typing import Set, Dict, List, Tuple, Any
from blochain_structures import Transaction, Stake, Block, Wallet, Chain, isvalidChain, weight_of_chain
from ipfs import addToIpfs, download_ipfs_file_subprocess
from flask_app import create_flask_app, run_flask_app
from ecdsa import VerifyingKey, BadSignatureError
from pathlib import Path

MAX_CONNECTIONS = 8
MAX_OUTPUT=2**256
EPOCH_TIME=60

class VrfThresholdException(Exception):
    pass

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

class Peer:
    def __init__(self, host, port, name, staker:bool):
        self.host = host
        self.name = name
        self.staker=staker

        self.port = port
        self.ipfs_port = port + 50  # API port
        self.gateway_port = port + 81  # Gateway port
        self.swarm_tcp = port + 2
        self.swarm_udp = port + 3
        self.repo_path = Path.home() / f".ipfs_{port}"
        self.env = os.environ.copy()
        self.env["IPFS_PATH"] = str(self.repo_path)

        self.server_connections :Set[websockets.WebSocketServerProtocol]=set() # For inbound peers ie websockets that connect to us and treat us as the server
        self.client_connections :Set[websockets.WebSocketServerProtocol]=set() # For outbound peers ie websockets we initiated, we are the clients

        self.outbound_peers: Set[tuple]=set()
        # The peers to which we currently maintain a outbound connection

        self.seen_message_ids: Set[str]= set()
        # Used to remove duplicate messages, messages that return to us after a round of broadcasting

        self.known_peers : Dict[Tuple[str, int], Tuple[str, str]]={} # (host, port):(name, public key)
        """
            We store all the peers we know here, we compare this with outbound peers in dicover_peers
            to find to which nodes we have not yet made a connection
        """
        
        self.staked_amt:int=0
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

        
        self.last_epoch_end_ts=datetime.now()
        self.mem_pool: Set[Transaction]=set()
        self.mem_pool_lock=asyncio.Lock() 
        
        self.file_hashes: Dict[str, str]={}
        self.file_hashes_lock=asyncio.Lock()
        self.daemon_process=None

        self.current_stakes: set[Stake]=set() # Public key is stored as pem string
        self.current_stakers:Dict[str, int]={}
        self.curr_stakers_condition=asyncio.Condition() 
        
        self.name_to_public_key_dict: Dict[str, str]={}
        
        self.wallet=Wallet()
        self.chain: Chain=None


        self.create_block_condition=asyncio.Condition()
        """
            Starts a timer for the creation of next block
        """
        self.mine_task=None

    async def send_peer_info(self, websocket):
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
                "public_key":self.wallet.public_key_pem
                }
        }

        self.seen_message_ids.add(pkt["id"])
        await websocket.send(json.dumps(pkt))

    async def send_known_peers(self, websocket):
        """
            Function for sending known_peers
            (information regarding all the peers we know)
        """
        peers=[{"host":h, "port":p, "name":n, "public_key":s}
               for (h, p), (n,s) in self.known_peers.items()]
        peers.append({"host":self.host, "port":self.port, "name":self.name, "public_key":self.wallet.public_key_pem})
        pkt={
            "type":"known_peers",
            "id":str(uuid.uuid4()),
            "peers":peers
        }
        self.seen_message_ids.add(pkt["id"])
        await websocket.send(json.dumps(pkt))

    def block_dict_to_block(self, block_dict:Dict[str, Any]):    
        """
            Verified whether given information in block_dict is valid and
            creates a block out of the information or returns None
            We sent a receive blocks as a dictionary
            block["trasnsactions"] is a list of dictionaries that
            represent transactions
        """

        new_block_id=block_dict.get("id")
        new_block_prevHash=block_dict.get("prevHash")
        new_block_ts=block_dict.get("ts")

        transactions=[]
        for transaction_dict in block_dict["transactions"]:
            transaction=Transaction(transaction_dict["amount"], transaction_dict["sender"], transaction_dict["receiver"], transaction_dict["id"], transaction_dict["ts"])
            if(transaction.sender!="Genesis"):
                transaction.sign=base64.b64decode(transaction_dict["sign"])
            transactions.append(transaction)
        
        if(not(new_block_id and new_block_ts and transactions)): # Genesis block doesn't have prevHash, it's an empty string
            return None
        
        newBlock=Block(new_block_prevHash, transactions, new_block_ts, new_block_id)   
        staked_amt=block_dict.get("staked_amt")
        if(staked_amt):
            newBlock.staked_amt=staked_amt

        if(block_dict.get("files")):
            newBlock.files=block_dict["files"]

        creator=block_dict.get("creator")
        if(creator):
            newBlock.creator=creator

        sign_b64=block_dict.get("sign")

        if(sign_b64):
            newBlock.sign=base64.b64decode(sign_b64)

        stakers_list:List[Stake]=[]
        for staker_dict in block_dict["stakers"]:
            new_Stake=self.stake_dict_to_stake(staker_dict)
            if(not new_Stake):
                continue
            stakers_list.append(new_Stake)
        
        vrf_proof=block_dict.get("vrf_proof_b64")
        seed=block_dict.get("seed")
        if(vrf_proof and seed):
            newBlock.vrf_proof=base64.b64decode(vrf_proof)
            newBlock.seed=seed

        newBlock.stakers=stakers_list
        return newBlock
    
    def stake_dict_to_stake(self, stake_dict:Dict[str, Any]):    
        """
            This function creates a stake out of the information
            stored inside stake_dict
        """
        id=stake_dict.get("id")
        staker=stake_dict.get("staker")
        amt=stake_dict.get("amt")
        ts=stake_dict.get("ts")
        sign=stake_dict.get("sign")

        if(not(id and staker and amt and sign)):
            return None
        
        stake=Stake(staker, amt, ts)
        stake.id=id

        sign_bytes=base64.b64decode(sign)        
        stake.sign=sign_bytes
        return stake

    async def handle_messages(self, websocket, msg):
        """
            This is a function to handle messages as the name suggests
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

        if t=="ping":
            # print("Received Ping")
            pkt={
                "type":"pong",
                "id":str(uuid.uuid4())
                }
            self.seen_message_ids.add(pkt["id"])
            await websocket.send(json.dumps(pkt))

        elif t=="pong":
            # print("Received Pong")
            self.got_pong[websocket]=True
            if not self.have_sent_peer_info.get(websocket, True):
                await self.send_peer_info(websocket)
                self.have_sent_peer_info[websocket]=True
            # print(f"[Sent peer]")

        elif t =='peer_info' or t == "add_peer":
            # print("Received Peer Info")
            data=msg["data"]
            normalized_self=normalize_endpoint((self.host, self.port))
            normalized_endpoint = normalize_endpoint((data['host'], data['port']))
            if normalized_endpoint not in self.known_peers and normalize_endpoint!=normalized_self :
                self.known_peers[normalized_endpoint]=(data['name'], data['public_key'])
                self.name_to_public_key_dict[data['name'].lower()]=data['public_key']
                print(f"Registered peer {data['name']} {data['host']}:{data['port']}")
                if t == 'peer_info':
                    await self.send_known_peers(websocket)
                    # print("Sent Known Peers")
                else:
                    await self.broadcast_message(msg)
                    await self.send_known_peers(websocket)

        elif t=="known_peers":
            # print("Received Known Peers")
            peers=msg["peers"]
            for peer in peers:
                normalized_self=normalize_endpoint((self.host, self.port))
                normalized_endpoint = normalize_endpoint((peer['host'], peer['port']))
                if normalized_endpoint not in self.known_peers and normalized_endpoint!=normalized_self:
                    print(f"Discovered peer {peer['name']} at {peer['host']}:{peer['port']}")
                    self.known_peers[normalized_endpoint]=(peer['name'], peer['public_key'])
                    self.name_to_public_key_dict[peer['name'].lower()]=peer['public_key']
            pkt={
                "type":"chain_request",
                "id":str(uuid.uuid4())
            }
            await websocket.send(json.dumps(pkt))

        elif t=="file":
            cid=msg["cid"]
            desc=msg["desc"]
            async with self.file_hashes_lock:
                self.file_hashes[cid]=desc

            await self.broadcast_message(msg)

        elif t=="new_tx":
            tx_str=msg["transaction"]
            tx=json.loads(tx_str)
            if(tx['amount']<=0):
                print("\nInvalid Transaction, amount<=0\n")
                return
            
            transaction: Transaction=Transaction(tx['amount'], tx['sender'], tx['receiver'], tx['id'], tx['ts'])
            if Chain.instance.transaction_exists_in_chain(transaction):
                print(f"{self.name} Transaction already exists in chain")
                return
            
            sign_bytes=base64.b64decode(msg["sign"])
            #b64decode turns bytes into a string
            if(transaction.amount>Chain.instance.calc_balance(transaction.sender, list(self.mem_pool), list(self.current_stakes))):
                print("\nAttempt to spend more than one has, Invalid transaction\n")
                return

            try:
                public_key=VerifyingKey.from_pem(msg['sender_pem'].encode())
                public_key.verify(
                    sign_bytes,
                    tx_str.encode()
                )
            except BadSignatureError as e:
                print("Invalid Signature")
                return
            
            transaction.sign=sign_bytes
            
            print("\nValid Transaction")
            print(f"\n{msg['type']}: {msg['transaction']}")
            print("\n")

            async with self.mem_pool_lock:
                self.mem_pool.add(transaction)
                # self.mem_pool_lock.notify_all()
            await self.broadcast_message(msg)

        elif t=="stake_announcement":
            stake_dict=msg.get("stake")
            if(not stake_dict):
                return
            
            if (not stake_dict.get("staker") and not stake_dict.get("amt")):
                return
            
            stake = Stake(stake_dict["staker"], stake_dict["amt"], stake_dict["ts"])
            stake.id=stake_dict.get("id")

            pid=stake.staker
            amt=stake.amt

            if(pid and amt):
                if amt<=0:
                    return
                
                sign=base64.b64decode(stake_dict["sign"])

                try:
                    vk=VerifyingKey.from_pem(pid)
                    vk.verify(sign, str(stake).encode())
                except BadSignatureError:
                    print("\nWrong signature\n")
                    return

                if(stake.amt>Chain.instance.calc_balance(stake.staker, list(self.mem_pool), list(self.current_stakes))):
                    print("\nInvalid stake, staked more than available\n")
                    return

                async with self.curr_stakers_condition:
                    self.current_stakes.add(stake)
                    self.current_stakers[pid]=int(amt)
                    print(f"New stake : {pid}:{amt}")
                await self.broadcast_message(msg)

        elif t=="new_block":
            new_block_dict=msg["block"]
            newBlock=self.block_dict_to_block(new_block_dict)

            if not Chain.instance.isValidBlock(newBlock):
                print("\nInvalid Block\n")
                return
            
            vk=VerifyingKey.from_pem(msg["block"]["creator"])
            vrf_proof=base64.b64decode(msg["vrf_proof"])
            sign=base64.b64decode(msg.get("sign"))

            print(f"\n{new_block_dict}\n")
            try:
                try:
                    vk.verify(vrf_proof, Chain.instance.epoch_seed().encode())
                except BadSignatureError as e:
                    print(f"\nInvalid Block (VRF_PROOF Signature Error), Stake should be slashed {e}\n")
                    return

                try:
                    vk.verify(sign, str(newBlock).encode())
                except BadSignatureError as e:
                    print(f"\nInvalid Block (Block Signature Error), Stake should be slashed {e}\n")
                    return
                
                if(newBlock.seed!=Chain.instance.epoch_seed()):
                    print("\nSeed May Have Been Altered\n")
                    return

                newBlock.sign=sign
                vrf_output=hashlib.sha256(vrf_proof).hexdigest()
                vrf_output_int=int(vrf_output, 16)
                staked_amt=self.current_stakers[msg["block"]["creator"]]
                total_amt_staked=sum(self.current_stakers.values())

                total_amt_staked_2=0
                for stake in newBlock.stakers:
                    vk=VerifyingKey.from_pem(stake.staker)
                    try:
                        print(f"\n{str(stake)}\n")
                        vk.verify(stake.sign, str(stake).encode())
                    except BadSignatureError as e:
                        print(f"\nInvalid Block (Stake Signature Error), Stake should be slashed {e}\n")
                        return

                    total_amt_staked_2+=stake.amt

                if(total_amt_staked>total_amt_staked_2):
                    print(f"\nSome stakes may have been ignored stakes_in_block 1:{total_amt_staked} 2:{total_amt_staked_2}\n")
                    return

                threshold=(staked_amt/total_amt_staked_2) * MAX_OUTPUT
                if(vrf_output_int>=threshold):
                    raise VrfThresholdException("VRF_Output is not less than threshold")
                newBlock.seed=Chain.instance.epoch_seed()
                newBlock.vrf_output=vrf_output
                newBlock.vrf_proof=vrf_proof
 
            except VrfThresholdException as e:
                print(f"\nInvalid Block (VRF_OUTPUT>THRESHOLD), Stake should be slashed {e}\n")
                return
            
            for transaction in newBlock.transactions:
                if transaction.amount>Chain.instance.calc_balance(publicKey=transaction.sender,current_stakes=newBlock.stakers):
                    print("\nInvalid Transactions, stake should be slashed\n")
                    return

            newBlock.creator=msg["block"]["creator"]
            Chain.instance.chain.append(newBlock)
            print("\n\n Block Appended \n\n")
            self.last_epoch_end_ts=datetime.now()

            async with self.mem_pool_lock:
                for transaction in list(self.mem_pool):
                    if newBlock.transaction_exists_in_block(transaction):
                        self.mem_pool.discard(transaction)
            
            async with self.file_hashes_lock:
                for hash in list(self.file_hashes.keys()):
                    if newBlock.cid_exists_in_block(hash):
                        self.file_hashes.pop(hash, None)
            
            self.staked_amt=0
            async with self.curr_stakers_condition:
                self.current_stakers.clear()
                self.current_stakes.clear()

            await self.broadcast_message(msg)

        elif t=="slash_announcement":
            block1_dict=msg.get("evidence1")
            block1=self.block_dict_to_block(block1_dict)
            block1.sign=base64.b64decode(msg.get("block1_sign"))
            vk=VerifyingKey.from_pem(block1.creator)
            
            block2_dict=msg.get("evidence2")
            block2=self.block_dict_to_block(block2_dict)
            block2.sign=base64.b64decode(msg.get("block2_sign"))

            block1_exists=Chain.instance.chain[msg["pos"]].is_equal(block1)
            block2_exists=Chain.instance.chain[msg["pos"]].is_equal(block2)
            if not (block1_exists or block2_exists):
                return

            err1, err2=False, False

            try:
                vk.verify(block1.sign, str(block1).encode())
            except BadSignatureError:
                print("\nBad signature on block 1\n")
                err1=True
            try:
                vk.verify(block2.sign, str(block2).encode())
            except BadSignatureError:
                print("\nBad signature on block 2\n")
                err2=True

            if(err1 and err2):
                Chain.instance.chain[pos].is_valid=False

            elif not(err1 or err2): # Both Signatures are correct
                Chain.instance.chain[pos].is_valid=False
                Chain.instance.chain[pos].slash_creator=True

            # Fork still exists but longest chain will win

            elif (err1 and not err2 and block1_exists) or (err2 and not err1 and block2_exists):
                Chain.instance.chain=Chain.instance.chain[:pos]
                # We trim the chain, eventually when a longer chain arrives it will replace this, but this is unlikely too since we don't share slash_announcement in such cases

        elif t=="chain_request":
            if(not Chain.instance):
                return

            pkt={
                "type":"chain",
                "id":str(uuid.uuid4()),
                "chain":Chain.instance.to_block_dict_list()
            }
            await websocket.send(json.dumps(pkt))

        elif t=="chain":
            print("Received a Chain")
            block_dict_list=msg["chain"]
            block_list: List[Block]=[]

            for block_dict in block_dict_list:
                block=self.block_dict_to_block(block_dict)
                block_list.append(block)

            if(not isvalidChain(block_list)):
                return

            #If chain doesn't already exist we assign this as the chain
            if not self.chain:
                self.chain=Chain(blockList=block_list)
                
            else:
                pos=Chain.instance.checkEquivalence(block_list)
                if(pos!=-1):
                    block1=Chain.instance.chain[pos]
                    block2=block_list[pos]

                    if(block1.creator!=block2.creator):# Non malicious fork
                        l1=len(Chain.instance.chain)
                        l2=len(block_list)
                        if(l2>l1):
                            Chain.instance.rewrite(block_list)
                    else:# Malicious fork
                        await self.verify_and_slash(block1, block2, pos, block_list)
                        
                elif(weight_of_chain(Chain.instance.chain)<weight_of_chain(block_list)):
                    Chain.instance.rewrite(block_list)
                    print("\nCurrent chain replaced by longer chain\n")
                
                else:
                    print("\nCurrent Chain Longer than received chain\n")

            async with self.mem_pool_lock:
                for transaction in list(self.mem_pool):
                    if Chain.instance.transaction_exists_in_chain(transaction):
                        self.mem_pool.discard(transaction)
            
            async with self.file_hashes_lock:
                for hash in list(self.file_hashes.keys()):
                    if(Chain.instance.cid_exists_in_chain(hash)):
                        self.file_hashes.pop(hash, None)

    async def verify_and_slash(self, block1:Block, block2:Block, pos:int, block_list:List[Block]):
        vk=VerifyingKey.from_pem(block1.creator)
        sign1=block1.sign
        sign2=block2.sign
        err1, err2=False, False

        try:
            vk.verify(sign1, str(block1).encode())
        except BadSignatureError:
            print("\nBad signature on block 1\n")
            err1=True
        try:
            vk.verify(sign2, str(block2).encode())
        except BadSignatureError:
            print("\nBad signature on block 2\n")
            err2=True
        

        if(err1 and not err2): # Unlikely since I'm checking blocks as they arrive
            Chain.instance.rewrite(block_list)
            return
        
        elif err2 and not err1: # Fault with arrived chain
            return
        
        Chain.instance.chain[pos].is_valid=False
        Chain.instance.chain[pos].slash_creator=True
        
        pkt={
            "type":"slash_announcement",
            "id":str(uuid.uuid4()),
            "evidence1":block1.to_dict_with_stakers(),
            "evidence2":block2.to_dict_with_stakers(),
            "block1_sign":base64.b64encode(block1.sign).decode(),
            "block2_sign":base64.b64encode(block2.sign).decode(),
            "pos":pos
        }
        await self.broadcast_message(pkt)
        # Now the receiver should make sure that the block1 creator signed both the blocks and it is he that is penalized in slash_block, also check my signature 
        # Then if Chain.instance.chain[pos]==block1 or block2 then make that block invalid and slash the creator
        
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
            self.server_connections.discard(websocket)
            await websocket.close()
            await websocket.wait_closed()

    async def broadcast_message(self, pkt):
        # For broadcasting messages to all the connections we have

        targets=self.server_connections | self.client_connections
        for ws in targets:
            try:
                await ws.send(json.dumps(pkt))

            except Exception as e:
                print(f"Error broadcasting: {e}")
                if ws in self.server_connections:
                    self.server_connections.discard(ws)
                else:
                    normalized_endpoint = normalize_endpoint((ws.remote_address[0], ws.remote_address[1]))
                    self.client_connections.discard(ws)
                    self.outbound_peers.discard(normalized_endpoint)
                    self.got_pong.pop(ws, None)
                    self.have_sent_peer_info.pop(ws, None)
                await ws.close()
                await ws.wait_closed()

    async def create_and_broadcast_tx(self, receiver_public_key, amt):
        """
            Function to create and broadcast transactions
        """
        transaction=Transaction(amt, self.wallet.public_key_pem, receiver_public_key)
        transaction_str=str(transaction)
        
        signature=self.wallet.private_key.sign(
            transaction_str.encode(),
        )

        transaction.sign=signature

        signature_b64=base64.b64encode(signature).decode()
        # b64encode returns bytes, Decode converts bytes to string
        
        pkt={
            "type":"new_tx",
            "id":str(uuid.uuid4()),
            "transaction":transaction_str,
            "sign":signature_b64,
            "sender_pem":self.wallet.public_key_pem # Already available as a pem string as defined in constructor
        }
        
        self.seen_message_ids.add(pkt["id"])
        if Chain.instance.transaction_exists_in_chain(transaction):
            return
        
        async with self.mem_pool_lock:
                self.mem_pool.add(transaction)

        print("Transaction Created", transaction)
        print("\n")
        await self.broadcast_message(pkt)

    async def user_input_handler(self):
        """
            A function to constantly take input from the user 
            about whom to send and how much
        """
        while True:
            print("Block Chain Menu\n***************")
            if(self.staker):
                print("0) Quit\n1) Add Transaction\n2) View balance\n3) Print Chain\n4) Print Pending Transactions\n5) Print Current Stakers\n6) Time since last epoch\n7) Send Files\n8) Download Files\n9) Stake\n")
            else:
                print("0) Quit\n1) Add Transaction\n2) View balance\n3) Print Chain\n4) Print Pending Transactions\5) Print Current Stakers\n6) Time since last epoch\n7) Send Files\n8) Download Files\n")

            ch= await asyncio._get_running_loop().run_in_executor(
                None, input, "Enter Your Choice: "
            )
            try:
                ch=int(ch)
            except:
                print("\nPlease enter a valid number!!!\n")

            if ch==1:
                rec= await asyncio._get_running_loop().run_in_executor(
                    None, input, "\nEnter Receiver's Name: "
                )

                amt= await asyncio._get_running_loop().run_in_executor(
                    None, input, "\nEnter Amount to send: "
                )
                
                receiver_public_key=self.name_to_public_key_dict.get(rec.lower().strip())
                if(receiver_public_key==None):
                    print("No such person available in directory...")
                    continue
                
                try:
                    amt=float(amt)
                except ValueError:
                    print("Amount must be a number")
                    continue
                
                if(amt<=0):
                    print("\nAmount must be positive\n")

                if amt<=Chain.instance.calc_balance(self.wallet.public_key_pem, list(self.mem_pool), list(self.current_stakes)):
                    await self.create_and_broadcast_tx(receiver_public_key, amt)
                else:
                    print("Insufficient Account Balance")
            
            elif ch==2:
                print("Account Balance =",Chain.instance.calc_balance(self.wallet.public_key_pem, list(self.mem_pool), list(self.current_stakes)))

            elif ch==3:
                i=0
                # We print all the blocks
                if(not Chain.instance):
                    print("\nChain hasn't been initialized yet\n")
                    continue
                for block in Chain.instance.chain:
                    print(f"block{i}: {block}\n")
                    i+=1

            elif ch==4:
                i=0
                for transaction in list(self.mem_pool):
                    print(f"transaction{i}: {transaction}\n\n")
                    i+=1

            elif ch==5:
                async with self.curr_stakers_condition:
                    print("\n")
                    for key in self.current_stakers:
                        print(f"{key}:{self.current_stakers[key]}\n")
                    print("\n")

            elif ch==6:
                print(f"\n{(datetime.now()-self.last_epoch_end_ts).seconds}\n")

            elif ch==7:
                desc= await asyncio._get_running_loop().run_in_executor(
                    None, input, "\nEnter description of file: "
                )
                path= await asyncio._get_running_loop().run_in_executor(
                    None, input, "\nEnter path of file: "
                )
                pkt=await self.uploadFile(desc, path)
                await self.broadcast_message(pkt)

            elif ch==8:
                cid= await asyncio._get_running_loop().run_in_executor(
                    None, input, "\nEnter cid of file: "
                )
                path= await asyncio._get_running_loop().run_in_executor(
                    None, input, "\nEnter path to download the file: "
                )
                download_ipfs_file_subprocess(cid, path)

            elif ch==9:
                if(not self.staker):
                    continue

                currTime=datetime.now()
                time_since=currTime-self.last_epoch_end_ts
                if(self.staked_amt>0):
                    print("Can't sent multiple stakes in one epoch")
                    continue

                if(time_since>timedelta(seconds=EPOCH_TIME*5/6)):
                    if(time_since>timedelta(seconds=EPOCH_TIME*7/6)):
                        self.last_epoch_end_ts=datetime.now()
                        self.staked_amt=0
                        self.current_stakers.clear()
                        self.current_stakes.clear()

                    else:
                        print(F"\nStake registration period closed, try again in the next epoch, time till next epoch : {EPOCH_TIME-time_since.seconds}\n")
                        continue

                amt= await asyncio._get_running_loop().run_in_executor(
                    None, input, "\nEnter Amount to stake: "
                )
                
                try:
                    amt=int(amt)
                    if(amt>Chain.instance.calc_balance(self.wallet.public_key_pem, list(self.mem_pool), list(self.current_stakes))):
                        print("\nInsufficient bank balance\n")
                        continue

                    await self.send_stake_announcements(amt)
                    self.staked_amt=amt
                    time_left=EPOCH_TIME-time_since.seconds
                    print(f"Creating block in {time_left} seconds")
                    asyncio.create_task(self.create_blocks(time_left))

                except ValueError as e:
                    print("\nPlease enter a valid number!!!\n", e)
                except Exception as e:
                    print("\nUnexpected error occured!!!\n", e)

            elif ch==0:
                print("Quitting...")
                break
    
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
        websocket=None
        
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
                        "public_key":self.wallet.public_key_pem
                    }
                }

                self.seen_message_ids.add(pkt["id"])
                await websocket.send(json.dumps(pkt))
                
            ping={
                "type":"ping",
                "id":str(uuid.uuid4()),
            }
            self.seen_message_ids.add(ping["id"])
            await websocket.send(json.dumps(ping))

            async for raw in websocket:
                msg=json.loads(raw)
                await self.handle_messages(websocket, msg)
        except Exception as e:
            print(f"Failed to connect to {host}:{port} ::: {e}")
            traceback.print_exc()
        finally:
            self.client_connections.discard(websocket)
            self.outbound_peers.discard(endpoint)
            self.got_pong.pop(websocket, None)
            self.have_sent_peer_info.pop(websocket, None)
            if(websocket):
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
            await asyncio.sleep(30)

    async def gossip_peer_sampler(self):
        """
            Every 60s, drops one existing peer and connects to one new peer.
        """
        while True:
            await asyncio.sleep(60)
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

    async def send_stake_announcements(self, amt: int):
        """
            Used for sending stake announcements
        """
        new_stake=Stake(self.wallet.public_key_pem, amt)
        stake_dict=new_stake.to_dict()

        sign=self.wallet.private_key.sign(str(new_stake).encode())
        new_stake.sign=sign

        stake_dict["sign"]=base64.b64encode(sign).decode()
        pkt={
            "id":str(uuid.uuid4()),
            "type":"stake_announcement",
            "public_key":self.wallet.public_key_pem,
            "stake":stake_dict
        }

        self.seen_message_ids.add(pkt["id"])
        async with self.curr_stakers_condition:
            self.current_stakers[self.wallet.public_key_pem]=amt
            self.current_stakes.add(new_stake)

        self.staked_amt=amt
        print("Stake Created")
        await self.broadcast_message(pkt)

    async def restart_epoch(self):
        while True:
            await asyncio.sleep(EPOCH_TIME/2)
            currTime=datetime.now()
            if(currTime-self.last_epoch_end_ts>timedelta(seconds=EPOCH_TIME*7/6)):
                self.last_epoch_end_ts=datetime.now()
                self.staked_amt=0
                self.current_stakers.clear()
                self.current_stakes.clear()

    async def create_blocks(self, time):
        if(not self.staker):
            print(self.staker)
            return
    
        await asyncio.sleep(time)
        if(len(self.current_stakers)<=0):
            print("\nNo stakers\n")
            self.last_epoch_end_ts=datetime.now()
            self.staked_amt=0
            return
        
        transactions_in_mem_pool=list(self.mem_pool)
        pending_transactions=[]
        for transaction in transactions_in_mem_pool:
            if(not Chain.instance.transaction_exists_in_chain(transaction)):
                pending_transactions.append(transaction)
        
        if(len(pending_transactions)<=0):
            print("\nNo pending transactions\n")
            self.last_epoch_end_ts=datetime.now()
            self.staked_amt=0
            async with self.curr_stakers_condition:
                self.current_stakers.clear()
                self.current_stakes.clear()
            return
        
        print("\nRunning vrf\n")
        async with self.curr_stakers_condition:# So that no new stakes don't comes in
            seed=Chain.instance.epoch_seed()
            vrf_proof=self.wallet.private_key.sign(seed.encode())
            vrf_output=hashlib.sha256(vrf_proof).hexdigest()
            vrf_output_int=int(vrf_output, 16)
            total_stake=sum(self.current_stakers.values())


            threshold=(self.staked_amt/total_stake)*MAX_OUTPUT
            if(vrf_output_int>=threshold):
                print("\nYou've lost\n")
                self.staked_amt=0
                return
            
            #The following code is for the winner
            print("\nYou won\n")
            newBlock=Block(Chain.instance.lastBlock.hash, pending_transactions)
            newBlock.files=self.file_hashes.copy()
            newBlock.seed=seed
            newBlock.vrf_proof=vrf_proof
            Chain.instance.chain.append(newBlock)
            newBlock.staked_amt=self.staked_amt
            newBlock.creator=self.wallet.public_key_pem
            newBlock.stakers=self.current_stakers
            

            self.last_epoch_end_ts=datetime.now()
            print("Block Appended")
            newBlock.stakers=list(self.current_stakes)
            # print(f"\n{newBlock.to_dict_with_stakers()}\n")

            self.staked_amt=0
            self.current_stakers.clear()
            self.current_stakes.clear()

            sign=self.wallet.private_key.sign(str(newBlock).encode())
            newBlock.sign=sign

            vrf_proof_b64=base64.b64encode(vrf_proof).decode()
            sign_b64=base64.b64encode(sign).decode()

            print(f"\n{newBlock.to_dict_with_stakers()}\n")
            pkt={
                "type":"new_block",
                "id":str(uuid.uuid4()),
                "block":newBlock.to_dict_with_stakers(),
                "vrf_proof":vrf_proof_b64,
                "sign":sign_b64,
            }

            self.seen_message_ids.add(pkt["id"])
            await self.broadcast_message(pkt)
        self.last_epoch_end_ts=datetime.now()

        async with self.mem_pool_lock:
            for transaction in list(self.mem_pool):
                if newBlock.transaction_exists_in_block(transaction):
                    self.mem_pool.discard(transaction)

        async with self.file_hashes_lock:
            for hash in list(self.file_hashes.keys()):
                if newBlock.cid_exists_in_block(hash):
                    self.file_hashes.pop(hash, None)
                                                       
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
            await asyncio.sleep(60)

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
            self.chain=Chain(publicKey=self.wallet.public_key_pem, privatekey=self.wallet.private_key)
            self.last_epoch_end_ts=datetime.now()

        # Create flask app
        flask_app = create_flask_app(self)
        flask_thread = threading.Thread(target=run_flask_app, args=(flask_app, self.port), daemon=True)
        flask_thread.start()

        reset_task=asyncio.create_task(self.restart_epoch())
        inp_task=asyncio.create_task(self.user_input_handler())
        consensus_task=asyncio.create_task(self.find_longest_chain())
        disc_task=asyncio.create_task(self.discover_peers())


        await inp_task

        reset_task.cancel()
        disc_task.cancel()
        consensus_task.cancel()
          
def strtobool(v):
    if isinstance(v, bool):
        return v

    if v.lower() in ("true", "yes", "1", "t"):
        return True

    elif v.lower() in ("false", "no", "0", "f"):
        return False

    raise argparse.ArgumentTypeError("Boolean Value Expected")    

def main():
    parser=argparse.ArgumentParser(description="Handshaker")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--name", default=None)
    parser.add_argument("--staker",type=strtobool, default=True)
    parser.add_argument("--connect", default=None)

    args=parser.parse_args()
    bootstrap_host, bootstrap_port=None, None

    if args.connect:
        try:
            bootstrap_host, bootstrap_port=args.connect.split(":")
            bootstrap_port=int(bootstrap_port)
        except ValueError:
            print("Invalid Bootstrap Format. Use host:port")
            return
    peer=Peer(args.host, args.port, args.name, args.staker)

    try:
        asyncio.run(peer.start(bootstrap_host, bootstrap_port))
    except KeyboardInterrupt:
        print("\nShutting Down...")

if __name__=="__main__":
    main()