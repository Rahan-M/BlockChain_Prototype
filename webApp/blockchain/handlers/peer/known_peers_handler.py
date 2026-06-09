import uuid

from webApp.blockchain.handlers.base_handler import BaseHandler
from webApp.blockchain.utils import normalize_endpoint

class KnownPeersHandler(BaseHandler):

    async def handle(self, websocket, msg):

        print("Known Peers Handler\n")

        peers = msg["peers"]

        if not peers:
            return
        
        normalized_self = normalize_endpoint((self.peer.host, self.peer.port))

        for peer in peers:

            if not all(k in peer for k in ['host', 'port', 'name', 'public_key', 'node_id']):
                continue
            
            normalized_endpoint = normalize_endpoint((peer['host'], peer['port']))
            if normalized_endpoint not in self.peer.network.known_peers and normalized_endpoint != normalized_self:
                print(f"Discovered peer {peer['name']} at {peer['host']}:{peer['port']}")
                self.peer.network.register_peer(peer)
        
        pkt = {
            "type": "chain_request",
            "id": str(uuid.uuid4())
        }

        await self.peer.network.send_message(websocket, pkt)