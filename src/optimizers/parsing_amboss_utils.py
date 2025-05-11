import json

def parse_amboss_data(data):
    """
    Simule le parsing de données Amboss.
    Retourne un dict si les données sont valides, lève une exception sinon.
    """
    if isinstance(data, str):
        # Simule un JSON corrompu
        raise ValueError("Invalid JSON format")
    if "channels" not in data or not isinstance(data["channels"], list):
        raise KeyError("Missing 'channels' field")
    # Vérifie que chaque channel a les champs requis
    for channel in data["channels"]:
        if "id" not in channel:
            raise KeyError("Missing 'id' in channel")
    return data 