import uuid

from webApp.blockchain.handlers.base_handler import BaseHandler

class PongHandler(BaseHandler):

    async def handle(self, websocket, msg):

        print("Pong Handler\n")

        self.peer.network.got_pong[websocket] = True
        
        if not self.peer.network.have_sent_peer_info.get(websocket, True):
                
            pkt={
                "type":"peer_info",
                "id":str(uuid.uuid4()),
                "data":{
                    "host" : self.peer.host,
                    "port" : self.peer.port,
                    "name" : self.peer.name,
                    "node_id" : self.peer.node_id,
                    "public_key" : self.peer.wallet.public_key_pem
                    
                    }
            }

            await self.peer.network.send_message(websocket, pkt)
            self.peer.network.have_sent_peer_info[websocket] = True