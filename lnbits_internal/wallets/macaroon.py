import binascii

def load_macaroon(macaroon: str) -> str:
    """
    Charge un macaroon LND (hex ou base64) et le retourne au format hexadécimal (string).
    """
    # Si le macaroon est déjà en hexadécimal (format classique LND)
    try:
        bytes_macaroon = binascii.unhexlify(macaroon)
        # Si la conversion réussit et la longueur est correcte, on retourne l'original
        if len(bytes_macaroon) > 10:
            return macaroon.lower()
    except Exception:
        pass
    # Sinon, on suppose que c'est du base64
    try:
        return binascii.hexlify(binascii.a2b_base64(macaroon)).decode().lower()
    except Exception:
        raise ValueError("Format de macaroon non reconnu (ni hex, ni base64)") 