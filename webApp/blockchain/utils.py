import socket
import random
import argparse

def normalize_endpoint(ep):
    """
        Return host resolved into ipv4 address and port converted into int datatype - maintains consistency in the code
    """
    host, port = ep
    return (socket.gethostbyname(host), int(port))

def get_random_element(s):
    """
        Return a random element from a set
    """
    import random
    return random.choice(list(s)) if s else None

def strtobool(v):
    if isinstance(v, bool):
        return v

    if v.lower() in ("true", "yes", "1", "t"):
        return True

    elif v.lower() in ("false", "no", "0", "f"):
        return False

    raise argparse.ArgumentTypeError("Boolean Value Expected")