import jwt
import os
from datetime import datetime, timedelta

# Configuration
SECRET_KEY = "bydeKu3eAd8YFBZwQBYOuHXwUGAZurlX"
payload = {
    "sub": "dazlng-user",
    "role": "user",
    "exp": datetime.utcnow() + timedelta(days=1)
}

# Génération du token
token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
print(f"\nToken JWT généré :\n{token}\n")
print("Utilisez ce token dans l'en-tête Authorization :")
print(f"Authorization: Bearer {token}") 