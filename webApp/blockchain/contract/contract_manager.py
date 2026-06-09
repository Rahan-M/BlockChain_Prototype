import hashlib

from webApp.blockchain.contract.secure_executor import SecureContractExecutor

GAS_PRICE = 0.001
BASE_DEPLOY_COST = 5
BASE_INVOKE_COST = 5

class ContractManager:
    def __init__(self, peer):
        self.contracts = {}
        self.peer = peer
    
    def calculate_contract_id(self, sender, timestamp):
        data = f"{sender}:{timestamp}"
        hash_object = hashlib.sha256(data.encode('utf-8'))
        return hash_object.hexdigest()

    def store_contract(self, contract_id, code):
        self.contracts[contract_id] = code

    def get_contract(self, contract_id):
        return self.contracts.get(contract_id)

    def get_deploy_cost(self, contract_code):
        gas_used = len(contract_code)//10 + BASE_DEPLOY_COST
        cost = gas_used * GAS_PRICE
        return cost

    def get_contract_state(self, contract_id):
        for block in reversed(self.peer.chain.chain):
            for transaction in reversed(block.transactions):
                if transaction.receiver == "invoke" and transaction.payload[0] == contract_id:
                    return transaction.payload[3]
        return {}

    def run_contract(self, contract_id, func_name, args):

        code = self.get_contract(contract_id)
        if code is None:
            raise Exception(f"Contract '{contract_id}' not found.")

        state = self.get_contract_state(contract_id)

        executor = SecureContractExecutor(code)
        response = executor.run(func_name, args, state)

        return response

    def get_invoke_cost_and_new_state(self, contract_id, func_name, args):

        response = self.run_contract(contract_id, func_name, args)
        if(response["error"] != None):
            error_msg = response["error"]
            raise Exception(f"Error: '{error_msg}'")

        new_state = response["state"]

        gas_used = response["gas_used"] + BASE_INVOKE_COST
        cost = gas_used * GAS_PRICE

        return cost, new_state
