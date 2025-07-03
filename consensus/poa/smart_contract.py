from RestrictedPython import compile_restricted
from RestrictedPython.Eval import default_guarded_getiter
from RestrictedPython.Guards import safe_builtins
from gas_meter import GasMeter
import math

def _getitem_(obj, index):
    return obj[index]

def _write_(obj):
    return obj

class ContractEnvironment:
    def __init__(self, code: str):
        self.code = code

        extended_builtins = dict(safe_builtins)
        extended_builtins.update({
            'set': set,
            'dict': dict,
            'list': list,
            'len': len,
            'range': range,
            'min': min,
            'max': max,
            'sum': sum,
            'abs': abs,
            'sorted': sorted,
            'enumerate': enumerate,
            'zip': zip,
            'any': any,
            'all': all,

            # math functions
            'sqrt': math.sqrt,
            'ceil': math.ceil,
            'floor': math.floor,
            'pow': pow,
            'fabs': math.fabs,
            'log': math.log,
            'log10': math.log10,
            'exp': math.exp,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'degrees': math.degrees,
            'radians': math.radians,
            'pi': math.pi,
            'e': math.e,
            'isclose': math.isclose,
            'gcd': math.gcd,
            'factorial': math.factorial,
        })

        self.globals = {
            '__builtins__': extended_builtins,
            '_getiter_': default_guarded_getiter,
            '_getitem_': _getitem_,
            '_write_': _write_,
        }
        self.locals = {}
        self._compile()

    def _compile(self):
        self.compiled = compile_restricted(self.code, filename='<contract>', mode='exec')
        exec(self.compiled, self.globals, self.locals)

    def run_contract(self, func_name: str, args, state):
        func = self.locals.get(func_name)
        if not func:
            raise Exception(f"Function '{func_name}' not found in contract.")
        
        gas_meter = GasMeter()

        try:
            gas_meter.start()
            state, msg = func(*args, state)
        finally:
            gas_meter.stop()

        return state, msg, gas_meter.gas_used