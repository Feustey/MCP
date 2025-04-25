class LNPlusError(Exception):
    """Classe de base pour les erreurs LN+"""
    pass

class LNPlusAPIError(LNPlusError):
    """Erreur lors de l'appel à l'API LN+"""
    pass

class LNPlusAuthError(LNPlusError):
    """Erreur d'authentification avec l'API LN+"""
    pass

class LNPlusValidationError(LNPlusError):
    """Erreur de validation des données"""
    pass

class LNPlusRateLimitError(LNPlusError):
    """Erreur de limite de taux d'appels"""
    pass

class LNPlusNetworkError(LNPlusError):
    """Erreur de réseau lors de l'appel à l'API LN+"""
    pass 