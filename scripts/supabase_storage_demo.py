import os
from supabase import create_client, Client

# Paramètres Supabase
url = "https://jjlgzltelraaaekxnomo.supabase.co"
key = os.getenv("SUPABASE_KEY")
email = os.getenv("SUPABASE_EMAIL")
password = os.getenv("SUPABASE_PASSWORD")

supabase: Client = create_client(url, key)

# Authentification utilisateur
try:
    login = supabase.auth.sign_in_with_password({"email": email, "password": password})
    print("Login OK. Token:", login.session.access_token[:40] + "...")
except Exception as e:
    print("Erreur lors du login:", e)
    exit(1)

# Upload d'un fichier
try:
    file_path = "rapport.pdf"  # Remplace par un fichier existant
    with open(file_path, "rb") as f:
        res = supabase.storage.from_("reports").upload(file_path, f)
    print("Upload OK:", res)
except Exception as e:
    print("Erreur lors de l'upload:", e)

# Download du même fichier
try:
    res = supabase.storage.from_("reports").download(file_path)
    with open("rapport_downloaded.pdf", "wb") as f:
        f.write(res)
    print("Download OK: rapport_downloaded.pdf")
except Exception as e:
    print("Erreur lors du download:", e) 