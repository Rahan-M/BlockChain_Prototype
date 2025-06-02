import asyncio, websockets, traceback, hashlib
import argparse, json, uuid, base64
import threading, socket
from datetime import datetime, timedelta
from typing import Set, Dict, List, Tuple
from blochain_structures import Transaction, Block, Wallet, Chain
from flask_app import create_flask_app, run_flask_app
from ecdsa import VerifyingKey, BadSignatureError

MAX_CONNECTIONS = 8
MAX_OUTPUT=2**256
EPOCH_TIME=60

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
        self.port = port
        self.name = name
        self.staker=staker

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
        
        self.current_stakers: Dict[str, int]={} # Public key is stored as pem string
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

        transactions=[]
        for transaction_dict in block_dict["transactions"]:
            transaction=Transaction(transaction_dict["amount"], transaction_dict["sender"], transaction_dict["receiver"], transaction_dict["id"])
            transactions.append(transaction)
        
        newBlock=Block(new_block_prevHash, transactions, new_block_ts, new_block_id)   
        return newBlock

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
            normalized_endpoint = normalize_endpoint((data["host"], data["port"]))
            if normalized_endpoint not in self.known_peers and normalize_endpoint!=normalized_self :
                self.known_peers[normalized_endpoint]=(data["name"], data["public_key"])
                self.name_to_public_key_dict[data["name"].lower()]=data["public_key"]
                print(f"Registered peer {data["name"]} {data["host"]}:{data["port"]}")
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
                normalized_endpoint = normalize_endpoint((peer["host"], peer["port"]))
                if normalized_endpoint not in self.known_peers and normalized_endpoint!=normalized_self:
                    print(f"Discovered peer {peer["name"]} at {peer["host"]}:{peer["port"]}")
                    self.known_peers[normalized_endpoint]=(peer["name"], peer["public_key"])
                    self.name_to_public_key_dict[peer["name"].lower()]=peer["public_key"]
            pkt={
                "type":"chain_request",
                "id":str(uuid.uuid4())
            }
            await websocket.send(json.dumps(pkt))

        elif t=="new_tx":
            tx_str=msg["transaction"]
            tx=json.loads(tx_str)
            transaction: Transaction=Transaction(tx['amount'], tx['sender'], tx['receiver'], tx['id'])
            if Chain.instance.transaction_exists_in_chain(transaction):
                print(f"{self.name} Transaction already exists in chain")
                return
            
            sign_bytes=base64.b64decode(msg["sign"])
            #b64decode turns bytes into a string
            if(transaction.amount>Chain.instance.calc_balance(transaction.sender, list(self.mem_pool))):
                print("\nAttempt to spend more than one has, Invalid transaction\n")
                return

            is_valid=True
            try:
                public_key=VerifyingKey.from_pem(msg['sender_pem'].encode())
                public_key.verify(
                    sign_bytes,
                    tx_str.encode()
                )
            except:
                is_valid=False


            if not is_valid:
                print("Invalid Signature")
                return
            
            print("\nValid Transaction")
            print(f"\n{msg['type']}: {msg['transaction']}")
            print("\n")

            async with self.mem_pool_lock:
                self.mem_pool.add(transaction)
                # self.mem_pool_lock.notify_all()
            await self.broadcast_message(msg)

        elif t=="stake_announcement":
            pid=msg.get("public_key")
            amt=msg.get("staked_amt")
            if(pid and amt):
                print("Hit here")
                async with self.curr_stakers_condition:
                    self.current_stakers[pid]=int(amt)
                    print(f"New stake : {pid}:{amt}")

        elif t=="new_block":
            new_block_dict=msg["block"]
            newBlock=self.block_dict_to_block(new_block_dict)
            vk=VerifyingKey.from_pem(msg["creator"])
            vrf_proof=base64.b64decode(msg["vrf_proof"])

            try:
                vk.verify(vrf_proof, Chain.instance.epoch_seed())

                vrf_output=hashlib.sha256(vrf_proof)
                staked_amt=self.current_stakers[msg["creator"]]
                total_amt_staked=sum(self.current_stakers.values())

                threshold=(staked_amt/total_amt_staked) * MAX_OUTPUT
                if(vrf_output>=threshold):
                    raise Exception("VRF_Output is not less than threshold")
                
            except (BadSignatureError, Exception) as e:
                print("\nInvalid Block, Stake should be slashed\n")
                return

            if Chain.instance.isValidBlock(newBlock):
                newBlock.creator=msg["creator"]
                Chain.instance.chain.append(newBlock)
                print("\n\n Block Appended \n\n")
                self.last_epoch_end_ts=datetime.now()

                async with self.mem_pool_lock:
                    for transaction in list(self.mem_pool):
                        if newBlock.transaction_exists_in_block(transaction):
                            self.mem_pool.discard(transaction)
                async with self.curr_stakers_condition:
                    self.current_stakers.clear()

                await self.broadcast_message(msg)

        elif t=="chain_request":
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

            #If chain doesn't already exist we assign this as the chain
            if not self.chain:
                self.chain=Chain(blockList=block_list)

            elif(len(Chain.instance.chain)<len(block_list)):
                Chain.instance.rewrite(block_list)
                print("\nCurrent chain replaced by longer chain")
            
            else:
                print("\nCurrent Chain Longer than received chain")
            async with self.mem_pool_lock:
                for transaction in list(self.mem_pool):
                    if Chain.instance.transaction_exists_in_chain(transaction):
                        self.mem_pool.discard(transaction)

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
                print("1) Add Transaction\n2) View balance\n3) Print Chain\n4) Print Pending Transactions\n5) Stake\n0) Quit")
            else:
                print("1) Add Transaction\n2) View balance\n3) Print Chain\n4) Print Pending Transactions\n0) Quit")

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
                
                if amt<=Chain.instance.calc_balance(self.wallet.public_key_pem, list(self.mem_pool)):
                    await self.create_and_broadcast_tx(receiver_public_key, amt)
                else:
                    print("Insufficient Account Balance")
            elif ch==2:
                print("Account Balance =",Chain.instance.calc_balance(self.wallet.public_key_pem, list(self.mem_pool)))
            elif ch==3:
                i=0
                # We print all the blocks
                for block in Chain.instance.chain:
                    print(f"block{i}: {block}\n")
                    i+=1            
            elif ch==4:
                i=0
                for transaction in list(self.mem_pool):
                    print(f"transaction{i}: {transaction}\n\n")
                    i+=1
            elif ch==5:
                currTime=datetime.now()
                if(currTime-self.last_epoch_end_ts>timedelta(seconds=EPOCH_TIME*5/6)):
                    print("\nStake registration period closed, try again in the next epoch\n")
                    continue

                amt= await asyncio._get_running_loop().run_in_executor(
                    None, input, "\nEnter Amount to stake: "
                )
                
                try:
                    amt=int(amt)
                    await self.send_stake_announcements(amt)
                    print("Sent stake")
                    self.staked_amt=amt
                    await self.create_blocks()
                except:
                    print("\nPlease enter a valid number!!!\n")

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
        pkt={
            "id":str(uuid.uuid4()),
            "type":"stake_announcement",
            "public_key":self.wallet.public_key_pem,
            "staked_amt":amt
        }

        self.seen_message_ids.add(pkt["id"])
        async with self.curr_stakers_condition:
            self.current_stakers[self.wallet.public_key_pem]=amt
        self.staked_amt=amt
        print("Stake Created")
        await self.broadcast_message(pkt)

    async def create_blocks(self):
        if(not self.staker):
            return
    
        await asyncio.sleep(EPOCH_TIME/6)
        if(len(self.current_stakers)<=0):
            print("\nNo stakers\n")
            self.last_epoch_end_ts=datetime.now()
            return
        
        transactions_in_mem_pool=List(self.mem_pool)
        pending_transactions=[]
        for transaction in transactions_in_mem_pool:
            if(not Chain.instance.transaction_exists_in_chain(transaction)):
                pending_transactions.append(transaction)
        
        if(len(pending_transactions)<=0):
            print("\nNo pending transactions\n")
            self.last_epoch_end_ts=datetime.now()
            return
        
        async with self.curr_stakers_condition:# So that no new stakes don't comes in
            message=Chain.instance.epoch_seed()
            vrf_proof=self.wallet.private_key.sign(message)
            vrf_output=hashlib.sha256(vrf_proof)
            total_stake=sum(self.current_stakers.values())

            threshold=(self.staked_amt/total_stake)*MAX_OUTPUT
            if(vrf_output>=threshold):
                print("\nYou've lost\n")
                return
            
            #The following code is for the winner
            newBlock=Block(Chain.instance.lastBlock.hash, pending_transactions)
            Chain.instance.chain.append(newBlock)
            print("Block Appended")
            newBlock.creator=self.wallet.public_key_pem

            vrf_proof_b64=base64.b64encode(vrf_proof).decode()
            pkt={
                "type":"new_block",
                "id":str(uuid.uuid4()),
                "block":newBlock.to_dict(),
                "creator":self.wallet.public_key_pem,
                "vrf_proof":vrf_proof_b64,
            }
            self.seen_message_ids.add(pkt["id"])
            await self.broadcast_message(pkt)
        self.last_epoch_end_ts=datetime.now()

        for transaction in list(self.mem_pool):
            if newBlock.transaction_exists_in_block(transaction):
                self.mem_pool.discard(transaction)
        
        asyncio.create_task(self.callOneSelf())

                            
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
            self.chain=Chain(publicKey=self.wallet.public_key_pem)
            self.last_epoch_end_ts=datetime.now()

        # Create flask app
        flask_app = create_flask_app(self)
        flask_thread = threading.Thread(target=run_flask_app, args=(flask_app, self.port), daemon=True)
        flask_thread.start()
        inp_task=asyncio.create_task(self.user_input_handler())
        consensus_task=asyncio.create_task(self.find_longest_chain())
        disc_task=asyncio.create_task(self.discover_peers())


        await inp_task

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