import asyncio, websockets, socket
from typing import Set, Dict, Tuple
import json
import uuid

MAX_CONNECTIONS = 8

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

class NetworkManager:

    def __init__(self, peer, known_peers = None):
        self.peer = peer

        self.server_connections :Set[websockets.WebSocketServerProtocol]=set()
        self.client_connections :Set[websockets.WebSocketServerProtocol]=set()
        self.outbound_peers: Set[tuple]=set()
        self.known_peers: Dict[Tuple[str, int], Tuple[str, str, str]] = known_peers or {} # (host, port):(name, public key, node id)

        self.got_pong: Dict[websockets.WebSocketServerProtocol, bool]={}
        self.have_sent_peer_info: Dict[websockets.WebSocketServerProtocol, bool]={}

    def get_unique_name(self, base_name):
        existing_names = []
        for key, value in self.known_peers.items():
            existing_names.append(value[0].lower())

        existing_names.append(self.peer.name)
        
        base_name = base_name.lower()
        if base_name not in existing_names:
            return base_name
        
        counter = 1
        while True:
            new_name = f"{base_name}{counter}"
            if new_name not in existing_names:
                return new_name
            counter += 1
    
    async def connect_to_peer(self, host, port):

        endpoint=(host, port)
        if endpoint in self.outbound_peers or endpoint==(self.peer.host, self.peer.port):
            return

        uri=f"ws://{host}:{port}"
        
        websocket = None
        try:
            websocket = await websockets.connect(uri)
            self.client_connections.add(websocket)
            self.outbound_peers.add(endpoint)
            self.have_sent_peer_info[websocket]=False

            print(f"Outbound connection formed to {host}:{port}")
            
            pkt = None
            # If connecting first time to the network, broadcasts node information to the entire network
            if self.peer.chain.chain == []:
                pkt={
                    "type":"add_peer",
                    "id":str(uuid.uuid4()),
                    "data":{
                        "host":self.peer.host,
                        "port":self.peer.port,
                        "name":self.peer.name,
                        "public_key":self.peer.wallet.public_key_pem,
                        "node_id":self.peer.node_id
                    }
                }
            else:
                pkt={
                    "type":"ping",
                    "id":str(uuid.uuid4()),
                } 

            self.peer.seen_message_ids.add(pkt["id"])
            await self.peer.send_message(websocket, pkt, True)

            async for raw in websocket:
                msg=json.loads(raw)
                await self.peer.handle_messages(websocket, msg)
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
                    if endpoint not in self.outbound_peers and endpoint != (self.peer.host, self.peer.port)
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
                if endpoint not in self.outbound_peers and endpoint != (self.peer.host, self.peer.port)
            }

            if potential_peers:
                new_peer = get_random_element(potential_peers)
                if new_peer:
                    print(f"Gossip Sampling: Connecting to new peer {new_peer}")
                    asyncio.create_task(self.connect_to_peer(*new_peer))

    def discard_server_connection_details(self, websocket):
        self.server_connections.discard(websocket)

    def discard_client_connection_details(self, websocket):
        normalized_endpoint = normalize_endpoint((websocket.remote_address[0], websocket.remote_address[1]))
        self.client_connections.discard(websocket)
        self.outbound_peers.discard(normalized_endpoint)
        self.got_pong.pop(websocket, None)
        self.have_sent_peer_info.pop(websocket, None)
