import os
from supabase import create_client, Client

# Remplace par tes vraies valeurs
url = "https://jjlgzltelraaaekxnomo.supabase.co"
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Création d'un compte utilisateur (modifie l'email à chaque test si besoin)
try:
    signup = supabase.auth.sign_up({"email": "feustey@pm.me", "password": "Smasher9-Pegboard1-Exemplify4-Quotable3-Undercut5"})
    print("Signup:", signup)
except Exception as e:
    print("Erreur lors du signup:", e)

# Connexion (login)
try:
    login = supabase.auth.sign_in_with_password({"email": "feustey@pm.me", "password": "Smasher9-Pegboard1-Exemplify4-Quotable3-Undercut5"})
    print("Login:", login)
except Exception as e:
    print("Erreur lors du login:", e) 