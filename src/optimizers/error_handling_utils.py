def handle_error(data):
    """
    Simule la gestion des erreurs pour différents cas de données.
    Retourne un message ou lève une exception selon le type d'erreur détectée.
    """
    if isinstance(data, str):
        raise ValueError("Données corrompues : format non valide")
    if not data:
        raise KeyError("Données absentes")
    if "capacity" in data and data["capacity"] < 0:
        raise ValueError("Donnée aberrante : capacité négative")
    return "OK" 