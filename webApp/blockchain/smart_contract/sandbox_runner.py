from blockchain.smart_contract.smart_contract import ContractEnvironment

def sandbox_contract_runner(code, func_name, args, state, return_dict):
    try:
        env = ContractEnvironment(code)
        state, msg, gas_used = env.run_contract(func_name, args, state)
        return_dict['state'] = state
        return_dict['msg'] = msg
        return_dict['gas_used'] = gas_used
        return_dict['error'] = None
    except Exception as e:
        return_dict['state'] = None
        return_dict['msg'] = None
        return_dict['gas_used'] = 0
        return_dict['error'] = str(e)