import os
import sys

REQUIRED_VARS = [
    "LIGHTNING_ADDRESS",
    "LNBITS_URL",
    "LNBITS_ADMIN_KEY",
    "LNBITS_INVOICE_KEY"
]

missing = [var for var in REQUIRED_VARS if not os.getenv(var)]
if missing:
    print(f"❌ Variables d'environnement manquantes : {', '.join(missing)}")
    sys.exit(1)
print("✅ Toutes les variables d'environnement critiques sont présentes.") 