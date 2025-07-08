class SmartContractDatabase:
    def __init__(self):
        self.contracts = {}
    
    def store_contract(self, contract_id, code):
        self.contracts[contract_id] = code

    def get_contract(self, contract_id):
        return self.contracts.get(contract_id)