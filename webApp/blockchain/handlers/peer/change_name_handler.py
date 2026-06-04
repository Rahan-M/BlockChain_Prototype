from webApp.blockchain.handlers.base_handler import BaseHandler

class ChangeNameHandler(BaseHandler):

    async def handle(self, websocket, msg):

        del self.peer.name_to_node_id_dict[self.peer.name]

        new_name = msg["new_name"]

        self.peer.name = new_name
        self.peer.name_to_node_id_dict[new_name] = self.peer.node_id
        self.peer.node_id_to_name_dict[self.peer.node_id] = new_name

        self.peer.seen_message_ids.add(msg["new_peer_msg_id"])