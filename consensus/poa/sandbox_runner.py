from smart_contract import ContractEnvironment

def sandbox_contract_runner(code, func_name, args, state, return_dict):
    try:
        env = ContractEnvironment(code)
        result, gas_used = env.run_contract(func_name, *args, state)
        return_dict['result'] = result
        return_dict['gas_used'] = gas_used
        return_dict['error'] = None
    except Exception as e:
        return_dict['result'] = None
        return_dict['gas_used'] = 0
        return_dict['error'] = str(e)