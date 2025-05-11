import asyncio, websockets, traceback
import argparse, json, uuid
from typing import Set, Dict, List, Tuple, Any

from blochain_structures import Transaction, Block, Wallet, Chain

class Peer:
    def __init__(self, host, port, name):
        self.host = host
        self.port = port
        self.name = name

        self.server_connections :Set[websockets.WebSocketServerProtocol]=set() # For inbound peers
        self.client_connections :Set[websockets.WebSocketServerProtocol]=set() # For outbound peers

        self.inbound_peers: Set[tuple]=set()
        self.outbound_peers: Set[tuple]=set()

        self.seen_message_ids: Set[str]= set()

        self.known_peers : Dict[Tuple[str, int], Tuple[str, str]]={} # (host, port):(name, public key)

        self.got_pong: Dict[websockets.WebSocketServerProtocol, bool]={}
        self.have_sent_peer_info: Dict[websockets.WebSocketServerProtocol, bool]={}
        self.mem_pool: Set[Transaction]=set()

        self.name_to_public_key_dict: Dict[str, str]={}
        
        self.wallet=Wallet()
        self.chain: Chain=None

        self.mem_pool_condition=asyncio.Condition()

    async def send_peer_info(self, websocket):
        pkt={
            "type":"peer_info",
            "id":str(uuid.uuid4()),
            "data":{
                "host":self.host,
                "port":self.port,
                "name":self.name,
                "public_key":self.wallet.public_key()
                }
        }

        self.seen_message_ids.add(pkt["id"])
        await websocket.send(json.dumps(pkt))

    async def send_known_peers(self, websocket):
        peers=[{"host":h, "port":p, "name":n, "public_key":s}
               for (h, p), (n,s) in self.known_peers.items()]
        peers.append({"host":self.host, "port":self.port, "name":self.name, "public_key":self.wallet.public_key})
        pkt={
            "type":"known_peers",
            "id":str(uuid.uuid4()),
            "peers":peers
        }
        self.seen_message_ids.add(pkt["id"])
        await websocket.send(json.dumps(pkt))

    def remove_websocket_info(self, websocket):
        endpoint=(websocket.remote_address[0], websocket.remote_address[1])
        self.client_connections.discard(websocket)
        self.server_connections.discard(websocket)
        self.outbound_peers.discard(endpoint)
        self.known_peers.pop(endpoint, None)
        self.got_pong.pop(websocket, None)
        self.have_sent_peer_info.pop(websocket, None)

    async def handle_messages(self, websocket, msg):
        t=msg.get("type")
        id=msg.get("id")

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

        if t=="pong":
            # print("Received Pong")
            self.got_pong[websocket]=True
            if not self.have_sent_peer_info[websocket]:
                await self.send_peer_info(websocket)
                self.have_sent_peer_info[websocket]=True
            # print(f"[Sent peer]")

        elif t =='peer_info':
            # print("Received Peer Info")
            data=msg["data"]
            if (data["host"], data["port"]) not in self.known_peers:
                self.known_peers[(data["host"], data["port"])]=(data["name"], data["public_key"])
                self.name_to_public_key_dict[data["name"].lower()]=data["public_key"]
                print(f"Registered peer {data["name"]} {data["host"]}:{data["port"]}")
                await self.send_known_peers(websocket)
                # print("Sent Known Peers")

        elif t=="known_peers":
            # print("Received Known Peers")
            peers=msg["peers"]
            for peer in peers:
                if (peer["host"], peer["port"]) not in self.known_peers and (peer["host"], peer["port"])!=(self.host, self.port):
                    print(f"Discovered peer {peer["name"]} at {peer["host"]}:{peer["port"]}")
                    self.known_peers[(peer["host"], peer["port"])]=(peer["name"], peer["public_key"])
                    self.name_to_public_key_dict[peer["name"].lower()]=peer["public_key"]

        elif t=="new_tx":
            tx_str=msg["transaction"]
            tx=json.loads(tx_str)
            transaction=Transaction(tx['amount'], tx['sender'], tx['receiver'], tx['id'])
            if Chain.instance.transaction_exists_in_chain(Transaction):
                print(f"{self.name} Transaction already exists in chain")
                return
            
            print(f"\n{msg["type"]}: {msg["transaction"]}")
            async with self.mem_pool_condition:
                self.mem_pool.add(transaction)
                self.mem_pool_condition.notify_all()
            await self.broadcast_message(msg)

    async def handle_connections(self, websocket):
        peer_addr=(websocket.remote_address[0], websocket.remote_address[1])
        self.server_connections.add(websocket)

        print(f"Inbound Connection from {peer_addr[0]}:{peer_addr[1]}")
        
        try:
            async for raw in websocket:
                msg=json.loads(raw)
                await self.handle_messages(websocket,msg)

        except websockets.exceptions.ConnectionClosed:
            print(f"Inbound Connection Closed: {peer_addr}")

        finally:
            self.remove_websocket_info(websocket)
            await websocket.close()
            await websocket.wait_closed()

    async def keep_pinging(self):
        ping={
            "type":"ping",
            "id":str(uuid.uuid4())
        }
        while True:
            for websocket in list(self.client_connections):
                try:
                    self.got_pong[websocket]=False
                    await websocket.send(json.dumps(ping))

                except :
                    print("Can't send ping...")
                    self.remove_websocket_info(websocket)
                    await websocket.close()
                    await websocket.wait_closed()

            await asyncio.sleep(15)
            
            for websocket in list(self.client_connections):
                if self.got_pong[websocket]:
                    continue
                self.remove_websocket_info(websocket)
                await websocket.close()
                await websocket.wait_closed()

            await asyncio.sleep(45)

    async def broadcast_message(self, pkt):
        targets=self.server_connections | self.client_connections
        for ws in targets:
            try:
                await ws.send(json.dumps(pkt))

            except Exception as e:
                print(f"Error broadcasting: {e}")
                host, port= ws.remote_address[0], ws.remote_address[1]
                self.server_connections.discard(ws)
                self.client_connections.discard(ws)
                self.outbound_peers.discard((host, port))
                self.known_peers.pop((host, port), None)
                self.got_pong.pop(ws, None)
                await ws.close()
                await ws.wait_closed()

    async def send_chat_message(self, msg):
        pkt={
            "type":"message",
            "id":str(uuid.uuid4()),
            "sender":self.name,
            "message":msg
        }
        self.seen_message_ids.add(pkt["id"])
        print(f"[{self.name}]: {msg}")
        await self.broadcast_message(pkt)

    async def create_and_broadcast_tx(self, receiver_public_key, amt):
        transaction=Transaction(amt, self.wallet.public_key, receiver_public_key)
        transaction_str=str(transaction)

        pkt={
            "type":"new_tx",
            "id":str(uuid.uuid4()),
            "transaction":transaction_str
        }

        websockets.send(json.dumps(pkt))

    async def user_input_handler(self):
        while True:
            rec= await asyncio._get_running_loop().run_in_executor(
                None, input, "\n Enter Receiver's Name (or /exit to quit): "
            )
            amt= await asyncio._get_running_loop().run_in_executor(
                None, input, "\n Enter Amount to send: : "
            )
            if rec.lower()=="/exit":
                print("Exiting...")
                break
            
            receiver_public_key=self.name_to_public_key_dict.get(rec.lower().strip())
            if(receiver_public_key==None):
                print("No such person available in directory...")
                continue
            
            try:
                amt=float(amt)
            except ValueError:
                print("Amount must be a number")
                continue

            await self.create_and_broadcast_tx(receiver_public_key, amt)
            
    async def connect_to_peer(self, host, port):
        endpoint=(host, port)
        if endpoint in self.outbound_peers or endpoint==(self.host, self.port):
            return

        uri=f"ws://{host}:{port}"
        
        try:
            websocket=await websockets.connect(uri)
            self.client_connections.add(websocket)
            self.outbound_peers.add(endpoint)
            self.have_sent_peer_info[websocket]=False

            print(f"Outbound connection formed to {host}:{port}")

            ping={
                "type":"ping",
                "id":str(uuid.uuid4()),
            }
            self.seen_message_ids.add(ping["id"])
            await websocket.send(json.dumps(ping))
            print("Sent Ping")

            async for raw in websocket:
                msg=json.loads(raw)
                await self.handle_messages(websocket, msg)
        except Exception as e:
            print(f"Failed to connect to {host}:{port} ::: {e}")
            traceback.print_exc()
        finally:
            self.outbound_peers.discard(endpoint)
            self.client_connections.discard(websocket)
            self.known_peers.pop(endpoint, None)
            self.got_pong.pop(websocket, None)
            await websocket.close()
            await websocket.wait_closed()

    async def discover_peers(self):
        for endpoint, name in list(self.known_peers.items()):
            if endpoint==(self.host, self.port):
                    continue
            if endpoint not in self.outbound_peers:
                print(f"Dialing known peer {name} at {endpoint}")
                await asyncio.create_task(self.connect_to_peer(endpoint[0], endpoint[1]))

    async def mine_blocks(self):
        while True:
            async with self.mem_pool_condition:
                await Chain.instance.mem_pool_condition.wait_for(lambda: len(Chain.instance.mem_pool) >= 3)
                # We check the about condition in lambda every time we get notified after a new transaction has been added

                if(len(self.mem_pool)>=3):
                    transaction_list=[]
                    for transaction in list(self.mem_pool):
                        if Chain.instance.transaction_exists_in_chain(transaction):
                            self.mem_pool.discard(transaction)
                            continue
                        else:
                            transaction_list.append(transaction)
                    if(len(transaction_list)>=3):
                        newBlock=Block(Chain.instance.lastBlock.hash, transaction_list)
                        sol=await asyncio.get_event_loop().run_in_executor(Chain.instance.mine(newBlock.nonce))
                        newBlock.solution=sol
                        #Broadcast block


    async def start(self, bootstrap_host=None, bootstrap_port=None):
        await websockets.serve(self.handle_connections, self.host, self.port)
        # We await the setting up of the server and the handle connections funciton,
        # This returns a websocket server object eventually

        if bootstrap_host and bootstrap_port:
            asyncio.create_task(self.connect_to_peer(bootstrap_host, bootstrap_port))
            asyncio.create_task(self.ask_for_chain(bootstrap_host, bootstrap_port))
        else:
            self.chain=Chain()

        ping_task=asyncio.create_task(self.keep_pinging())
        inp_task=asyncio.create_task(self.user_input_handler())
        disc_task=asyncio.create_task(self.discover_peers())
        mine_task=asyncio.create_task(self.mine_blocks())
        await inp_task
        disc_task.cancel()
        ping_task.cancel()

def main():
    parser=argparse.ArgumentParser(description="Handshaker")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--name", default=None)
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
    peer=Peer(args.host, args.port, args.name)

    try:
        asyncio.run(peer.start(bootstrap_host, bootstrap_port))
    except KeyboardInterrupt:
        print("\nShutting Down...")

if __name__=="__main__":
    main()