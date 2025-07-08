import sys

GAS_LIMIT = 10000

class GasMeter:
    def __init__(self):
        self.gas_used = 0

    def tracer(self, frame, event, arg):
        if event == "line":
            self.gas_used += 1
            if self.gas_used > GAS_LIMIT:
                raise Exception("Out of gas")
        return self.tracer

    def start(self):
        sys.settrace(self.tracer)

    def stop(self):
        sys.settrace(None)