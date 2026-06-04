from webApp.blockchain.blockchain_structures.transaction import Transaction

class CommonChain:
    @property
    def lastBlock(self):
        return self.chain[-1]
    
    def to_block_dict_list(self):
        return [block.to_dict() for block in self.chain]

    def transaction_exists_in_chain(self, transaction: Transaction):
        for block in reversed(self.chain):
            if block.transaction_exists_in_block(transaction):
                return True
        
        return False

    def cid_exists_in_chain(self, cid: str):
        for block in reversed(self.chain):
            if block.cid_exists_in_block(cid):
                return True
        
        return False