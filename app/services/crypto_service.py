import os
from lnbits_internal.utils.crypto import AESCipher

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "VOTRE_CLE_CHIFFREMENT")

def encrypt_data(data: dict) -> str:
    import json
    cipher = AESCipher(key=ENCRYPTION_KEY)
    return cipher.encrypt(json.dumps(data).encode())

def decrypt_data(encrypted: str) -> dict:
    import json
    cipher = AESCipher(key=ENCRYPTION_KEY)
    return json.loads(cipher.decrypt(encrypted)) 