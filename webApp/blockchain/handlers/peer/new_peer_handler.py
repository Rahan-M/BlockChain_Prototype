from webApp.blockchain.handlers.base_handler import BaseHandler
from webApp.blockchain.utils import normalize_endpoint

class NewPeerHandler(BaseHandler):

    async def handle(self, websocket, msg):

        data=msg["data"]

        normalized_self = normalize_endpoint((self.peer.host, self.peer.port))
        normalized_endpoint = normalize_endpoint((data["host"], data["port"]))

        if normalized_endpoint not in self.peer.network.known_peers and normalized_endpoint != normalized_self:

            self.peer.network.register_peer(data)
            self.peer.save_known_peers_to_disk()
            print(f"Registered peer {data['name']} {data['host']}:{data['port']}")

            await self.peer.network.broadcast_message(msg)