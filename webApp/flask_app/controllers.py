# flask_app/controllers.py
from flask import request, jsonify
import asyncio
from ecdsa import SECP256k1, SigningKey
  
async def create_keys():
    private_key = SigningKey.generate(curve=SECP256k1)
        
    private_key_pem = private_key.to_pem().decode()

    public_key = private_key.get_verifying_key()

    public_key_pem = public_key.to_pem().decode()

    return jsonify({"message": "Success", "vk":public_key_pem, "sk": private_key_pem})
