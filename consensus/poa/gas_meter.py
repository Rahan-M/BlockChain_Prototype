import sys

class GasMeter:
    def __init__(self, gas_limit):
        self.gas_limit = gas_limit
        self.gas_used = 0

    def tracer(self, frame, event, arg):
        if event == "line":
            self.gas_used += 1
            if self.gas_used > self.gas_limit:
                raise Exception("Out of gas")
        return self.tracer

    def start(self):
        sys.settrace(self.tracer)

    def stop(self):
        sys.settrace(None)