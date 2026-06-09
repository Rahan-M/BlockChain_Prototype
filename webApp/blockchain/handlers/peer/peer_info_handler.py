import uuid

from webApp.blockchain.handlers.base_handler import BaseHandler
from webApp.blockchain.utils import normalize_endpoint

class PeerInfoHandler(BaseHandler):

    async def handle(self, websocket, msg):

        data = msg["data"]

        normalized_self = normalize_endpoint((self.peer.host, self.peer.port))
        normalized_endpoint = normalize_endpoint((data["host"], data["port"]))

        if normalized_endpoint not in self.peer.network.known_peers and normalized_endpoint != normalized_self:

            self.peer.network.register_peer(data)
            print(f"Registered peer {data['name']} {data['host']}:{data['port']}")

            known_peers=[{"host":h, "port":p, "name":n, "public_key":s, "node_id":i}
                for (h, p), (n, s, i) in self.peer.network.known_peers.items()]
            known_peers.append({"host":self.peer.host, "port":self.peer.port, "name":self.peer.name, "public_key":self.peer.wallet.public_key_pem, "node_id":self.peer.node_id})
            
            pkt = {
                "type" : "known_peers",
                "id" : str(uuid.uuid4()),
                "peers" : known_peers
            }

            await self.peer.network.send_message(websocket, pkt)
        