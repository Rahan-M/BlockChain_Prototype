import uuid

from webApp.blockchain.handlers.base_handler import BaseHandler
from webApp.blockchain.utils import normalize_endpoint

class KnownPeersHandler(BaseHandler):

    async def handle(self, websocket, msg):

        peers = msg["peers"]

        if not peers:
            return
        
        new_peer_found = False
        normalized_self = normalize_endpoint((self.peer.host, self.peer.port))

        for peer in peers:

            if not all(k in peer for k in ['host', 'port', 'name', 'public_key']):
                continue
            
            normalized_endpoint = normalize_endpoint((peer['host'], peer['port']))
            if normalized_endpoint not in self.peer.known_peers and normalized_endpoint != normalized_self:
                print(f"Discovered peer {peer['name']} at {peer['host']}:{peer['port']}")
                new_peer_found = True
                self.peer.network.register_peer(peer)

        if new_peer_found:
            self.peer.save_known_peers_to_disk()
        
        pkt = {
            "type": "chain_request",
            "id": str(uuid.uuid4())
        }

        await self.peer.network.send_message(websocket, pkt)