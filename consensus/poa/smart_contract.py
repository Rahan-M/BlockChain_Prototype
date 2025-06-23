from RestrictedPython import compile_restricted
from RestrictedPython.Eval import default_guarded_getiter
from RestrictedPython.Guards import safe_builtins
from RestrictedPython.PrintCollector import PrintCollector
from gas_meter import GasMeter

GAS_LIMIT = 100

def _getitem_(obj, index):
    return obj[index]

def _write_(obj):
    return obj

class ContractEnvironment:
    def __init__(self, code: str):
        self.code = code
        self.globals = {
            '__builtins__': safe_builtins,
            '_getiter_': default_guarded_getiter,
            '_getitem_': _getitem_,
            '_write_': _write_,
            '_print_': PrintCollector,
        }
        self.locals = {}
        self._compile()

    def _compile(self):
        self.compiled = compile_restricted(self.code, filename='<contract>', mode='exec')
        exec(self.compiled, self.globals, self.locals)

    def run_contract(self, func_name: str, *args):
        func = self.locals.get(func_name)
        if not func:
            raise Exception(f"Function '{func_name}' not found in contract.")
        
        gas_meter = GasMeter(GAS_LIMIT)

        try:
            gas_meter.start()
            result = func(*args)
        finally:
            gas_meter.stop()

        return result, gas_meter.gas_used