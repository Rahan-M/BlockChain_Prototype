from typing import List

from webApp.blockchain.handlers.base_handler import BaseHandler
from webApp.blockchain.blockchain_structures.block.pow.pow import Block
from webApp.blockchain.blockchain_structures.chain.pow.utils import isvalidChain

class PoWChainHandler(BaseHandler):

    async def handle(self, websocket, msg):
        print("Received a Chain")
        block_dict_list=msg["chain"]
        block_list: List[Block]=[]


        for block_dict in block_dict_list:
            block=self.peer.block_dict_to_block(block_dict)
            block_list.append(block)

        if not isvalidChain(block_list):
            print("\nInvalid Chain\n")
            return

        #If chain doesn't already exist we assign this as the chain
        if self.peer.chain.chain == []:
            self.peer.chain.rewrite(block_list)
            self.peer.save_chain_to_disk()
            return                 

        elif(len(self.peer.chain.chain)<len(block_list)):
            self.peer.chain.rewrite(block_list)
            print("\nCurrent chain replaced by longer chain")
            self.peer.save_chain_to_disk()
        else:
            print("\nCurrent Chain Longer than received chain")

        async with self.peer.mem_pool_condition:
            for transaction in self.peer.mem_pool:
                if self.peer.chain.transaction_exists_in_chain(transaction):
                    self.peer.mem_pool.remove(transaction)

        async with self.peer.ipfs.file_hashes_lock:
            for hash in list(self.peer.ipfs.file_hashes.keys()):
                if(self.peer.chain.cid_exists_in_chain(hash)):
                    self.peer.ipfs.file_hashes.pop(hash, None)
