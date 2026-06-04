from webApp.blockchain.handlers.connection.ping_handler import PingHandler
from webApp.blockchain.handlers.connection.pong_handler import PongHandler

from webApp.blockchain.handlers.peer.peer_info_handler import PeerInfoHandler
from webApp.blockchain.handlers.peer.add_peer_handler import AddPeerHandler
from webApp.blockchain.handlers.peer.new_peer_handler import NewPeerHandler
from webApp.blockchain.handlers.peer.change_name_handler import ChangeNameHandler

from webApp.blockchain.handlers.blockchain.transaction_handler import TransactionHandler

from webApp.blockchain.handlers.blockchain.chain_request_handler import ChainRequestHandler

from webApp.blockchain.handlers.ipfs.file_handler import FileHandler

from webApp.blockchain.handlers.poa.network_details_handler import NetworkDetailsHandler
from webApp.blockchain.handlers.poa.network_details_request_handler import NetworkDetailsRequestHandler

from webApp.blockchain.handlers.poa.miners_list_handler import MinersListHandler

from webApp.blockchain.handlers.pos.stake_announcement_handler import StakeAnnouncementHandler
from webApp.blockchain.handlers.pos.slash_announcement_handler import SlashAnnouncementHandler

from webApp.blockchain.handlers.pow.block_handler import PoWBlockHandler
from webApp.blockchain.handlers.pow.chain_handler import PoWChainHandler

from webApp.blockchain.handlers.pos.block_handler import PoSBlockHandler
from webApp.blockchain.handlers.pos.chain_handler import PoSChainHandler

from webApp.blockchain.handlers.poa.block_handler import PoABlockHandler
from webApp.blockchain.handlers.poa.chain_handler import PoAChainHandler

from webApp.blockchain.handlers.peer.known_peers_handler import KnownPeersHandler
from webApp.blockchain.handlers.poa.known_peers_handler import PoAKnownPeersHandler

class MessageRouter:

    def __init__(self, peer):
        self.peer = peer

        consensus = self.peer.consensus

        if consensus == "poa":
            self.block_handler = PoABlockHandler(peer)
            self.chain_handler = PoAChainHandler(peer)
            self.known_peers_handler = PoAKnownPeersHandler(peer)
        elif consensus == "pos":
            self.block_handler = PoSBlockHandler(peer)
            self.chain_handler = PoSChainHandler(peer)
            self.known_peers_handler = KnownPeersHandler(peer)
        elif consensus == "pow":
            self.block_handler = PoWBlockHandler(peer)
            self.chain_handler = PoWChainHandler(peer)
            self.known_peers_handler = KnownPeersHandler(peer)

        self.handlers = {
            "ping": PingHandler(peer),
            "pong": PongHandler(peer),

            "peer_info": PeerInfoHandler(peer),
            "add_peer": AddPeerHandler(peer),
            "new_peer": NewPeerHandler(peer),
            "known_peers": self.known_peers_handler,
            "change_name": ChangeNameHandler(peer),

            "new_tx": TransactionHandler(peer),
            "new_block": self.block_handler,
            "chain": self.chain_handler,
            "chain_request": ChainRequestHandler(peer),

            "file": FileHandler(peer),

            "miners_list_update": MinersListHandler(peer),

            "network_details": NetworkDetailsHandler(peer),
            "network_details_request": NetworkDetailsRequestHandler(peer),

            "stake_announcement": StakeAnnouncementHandler(peer),
            "slash_announcement": SlashAnnouncementHandler(peer),
        }

    async def handle(self, websocket, msg):

        t = msg.get("type")
        msg_id = msg.get("id")

        if not t or not msg_id:
            return

        if msg_id in self.peer.seen_message_ids:
            return

        self.peer.seen_message_ids.add(msg_id)

        handler = self.handlers.get(t)

        if not handler:
            return

        await handler.handle(websocket, msg)