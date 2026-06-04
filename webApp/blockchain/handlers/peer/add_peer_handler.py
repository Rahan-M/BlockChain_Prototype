import uuid

from webApp.blockchain.handlers.base_handler import BaseHandler
from webApp.blockchain.utils import normalize_endpoint

class AddPeerHandler(BaseHandler):

    async def handle(self, websocket, msg):

        data = msg["data"]

        # normalize
        normalized_self = normalize_endpoint((self.peer.host, self.peer.port))
        normalized_endpoint = normalize_endpoint((data["host"], data["port"]))

        new_peer_msg_id = str(uuid.uuid4())

        if normalized_endpoint not in self.peer.network.known_peers and normalized_endpoint != normalized_self :

            # get unique name
            proposed_name = self.peer.network.get_unique_name(data["name"])

            if proposed_name != data["name"]:
                pkt={
                    "type" : "change_name",
                    "id" : str(uuid.uuid4()),
                    "new_peer_msg_id" : new_peer_msg_id,
                    "new_name": proposed_name
                }
                await self.peer.network.send_message(websocket, pkt)
                data["name"] = proposed_name

            # add peer
            self.peer.network.register_peer(data)
            self.peer.save_known_peers_to_disk()

            print(f"Registered peer {data['name']} {data['host']}:{data['port']}")
            
            # send known peers list to new peer
            known_peers = self.peer.get_known_peers()
            known_peers.append({
                "host" : self.peer.host,
                "port" : self.peer.port,
                "name" : self.peer.name,
                "public_key" : self.peer.wallet.public_key_pem,
                "node_id" : self.peer.node_id
            })
            known_peers_pkt = {
                "type" : "known_peers",
                "id" : str(uuid.uuid4()),
                "peers" : known_peers
            }
            await self.peer.network.send_message(websocket, known_peers_pkt)

            # broadcast new peer details
            new_peer_pkt = {
                "type" : "new_peer",
                "id" : new_peer_msg_id,
                "data":{
                    "host" : data["host"],
                    "port" : data["port"],
                    "name" : data["name"],
                    "public_key" : data["public_key"],
                    "node_id" : data["node_id"]
                }
            }
            await self.peer.network.broadcast_message(new_peer_pkt)