class SmartContractDatabase:
    def __init__(self):
        self.contracts = {}
        self.contract_states = {}
    
    def store_contract(self, contract_id, code):
        self.contracts[contract_id] = code
        self.contract_states[contract_id] = {}

    def get_contract(self, contract_id):
        return self.contracts.get(contract_id)
    
    def get_contract_state(self, contract_id):
        return self.contract_states.get(contract_id, {})
    
    def update_contract_state(self, contract_id, new_state):
        self.contract_states[contract_id] = new_state