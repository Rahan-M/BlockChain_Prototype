from ecdsa import VerifyingKey, SigningKey, SECP256k1

class WalletManager:
    def __init__(self, peer, private_key_pem: str = None):

        if not private_key_pem:
            self.private_key = SigningKey.generate(curve=SECP256k1)
        else:
            self.private_key = SigningKey.from_pem(private_key_pem)
            
        self.private_key_pem = self.private_key.to_pem().decode()

        self.public_key = self.private_key.get_verifying_key()

        self.public_key_pem = self.public_key.to_pem().decode()
