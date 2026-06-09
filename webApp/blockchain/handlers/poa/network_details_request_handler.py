import uuid

from webApp.blockchain.handlers.base_handler import BaseHandler

class NetworkDetailsRequestHandler(BaseHandler):

    async def handle(self, websocket, msg):

        print("Network Details Request Handler\n")

        pkt={
            "type": "network_details",
            "id": str(uuid.uuid4()),
            "admin": self.peer.admin_id,
            "miners": self.peer.miners
        }

        await self.peer.network.send_message(websocket, pkt)