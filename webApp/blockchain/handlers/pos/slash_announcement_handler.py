import base64

from webApp.blockchain.handlers.base_handler import BaseHandler
from ecdsa import VerifyingKey, BadSignatureError

class SlashAnnouncementHandler(BaseHandler):

    async def handle(self, websocket, msg):
    
        block1_dict = msg.get("evidence1")
        block1_sign = msg.get("block1_sign")
        block2_dict = msg.get("evidence2")
        block2_sign = msg.get("block2_sign")
        pos = msg.get("pos")
        
        if not all([block1_dict, block1_sign, block2_dict, block2_sign, pos is not None]):
            return
        
        block1 = self.peer.block_dict_to_block(block1_dict)
        try:
            block1.sign = base64.b64decode(block1_sign)
        except Exception:
            return
        
        if not hasattr(block1, 'creator') or not block1.creator:
            return
        
        vk = VerifyingKey.from_pem(block1.creator)
        
        block2 = self.peer.block_dict_to_block(block2_dict)
        try:
            block2.sign = base64.b64decode(block2_sign)
        except Exception:
            return

        if pos < 0 or pos >= len(self.peer.chain.chain):
            return

        block1_exists = self.peer.chain.chain[pos].is_equal(block1)
        block2_exists = self.peer.chain.chain[pos].is_equal(block2)
        if not (block1_exists or block2_exists):
            return

        err1, err2 = False, False

        try:
            vk.verify(block1.sign, str(block1).encode())
        except BadSignatureError:
            print("\nBad signature on block 1\n")
            err1 = True
        try:
            vk.verify(block2.sign, str(block2).encode())
        except BadSignatureError:
            print("\nBad signature on block 2\n")
            err2 = True

        if err1 and err2:
            print(f"\nInvalid Slashing Evidence")
            return
        
        elif not(err1 or err2) and self.peer.chain.chain[pos].is_valid:  # Both Signatures are correct and not slashed yet
            print(f"\nBlock {pos} slashed\n")
            self.peer.chain.chain[pos].is_valid = False
            self.peer.chain.chain[pos].slash_creator = True
            await self.peer.network.broadcast_message(msg)

        # Fork still exists but longest chain will win

        elif (err1 and not err2 and block1_exists) or (err2 and not err1 and block2_exists):
            self.peer.chain.chain = self.peer.chain.chain[:pos]
            self.peer.save_chain_to_disk()
            # We trim the chain, eventually when a longer chain arrives it will replace this, but this is unlikely too since we don't share slash_announcement in such cases
            # hmm this means err1 exists but block1 also exists so we trim back to before that block
            # :pos is not included
