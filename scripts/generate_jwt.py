import jwt
import sys
from datetime import datetime, timedelta

# À adapter : même clé et algo que dans app/auth.py
SECRET_KEY = "VOTRE_CLE_SECRETE_A_REMPLACER"
ALGORITHM = "HS256"

if len(sys.argv) < 2:
    print("Usage: python scripts/generate_jwt.py <tenant_id> [expiration_minutes]")
    sys.exit(1)

tenant_id = sys.argv[1]
expiration_minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 60

payload = {
    "tenant_id": tenant_id,
    "exp": datetime.utcnow() + timedelta(minutes=expiration_minutes)
}

token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
print(token) 