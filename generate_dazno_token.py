#!/usr/bin/env python3
"""
Script de génération de tokens JWT pour dazno.de
Génère des tokens JWT valides pour l'API MCP avec tenant isolation

Usage:
    python generate_dazno_token.py --user-id USER_ID --tenant-id TENANT_ID
    python generate_dazno_token.py --user-id USER_ID --tenant-id TENANT_ID --expire-hours 48
    python generate_dazno_token.py --verify TOKEN  # Vérifie un token existant

Dernière mise à jour: 7 janvier 2025
"""

import secrets
import argparse
import sys

try:
    import jwt
except ImportError:
    try:
        import PyJWT as jwt
    except ImportError:
        print("Erreur: PyJWT n'est pas installé. Installez-le avec: pip install PyJWT")
        print("   ou: pip3 install PyJWT")
        sys.exit(1)
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Configuration JWT de production pour dazno.de
# Secret depuis config/credentials-production.md
JWT_SECRET = "xiFWGli2ZPbW1DVhSZ/b8G2XV9H/7yix+ypdKOTnRhYUeWe5gi4XVZoyH0LUsjNO9BckE1JCDjAFWb4P2moS9Q=="
JWT_ALGORITHM = "HS256"
DEFAULT_EXPIRATION_HOURS = 24

# Émetteur et audience selon la configuration
JWT_ISSUER = "app.dazno.de"
JWT_AUDIENCE = "api.dazno.de"


def create_dazno_jwt_token(
    user_id: str,
    tenant_id: str,
    permissions: list = None,
    expire_hours: int = DEFAULT_EXPIRATION_HOURS
) -> str:
    """
    Crée un token JWT valide pour l'API MCP dazno.de
    
    Args:
        user_id: Identifiant de l'utilisateur
        tenant_id: Identifiant du tenant (pour isolation des données)
        permissions: Liste des permissions (optionnel)
        expire_hours: Nombre d'heures avant expiration (défaut: 24)
    
    Returns:
        Token JWT signé
    """
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=expire_hours)
    
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "permissions": permissions or ["read", "write"],
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": secrets.token_hex(16)  # JWT ID unique
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def verify_token(token: str) -> Dict[str, Any]:
    """
    Vérifie et décode un token JWT
    
    Args:
        token: Token JWT à vérifier
    
    Returns:
        Dictionnaire avec les informations du token décodé
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE
        )
        
        exp_timestamp = payload.get("exp", 0)
        exp_datetime = datetime.fromtimestamp(exp_timestamp)
        
        return {
            "valid": True,
            "payload": payload,
            "user_id": payload.get("sub"),
            "tenant_id": payload.get("tenant_id"),
            "permissions": payload.get("permissions", []),
            "issued_at": datetime.fromtimestamp(payload.get("iat", 0)),
            "expires_at": exp_datetime,
            "is_expired": exp_datetime < datetime.utcnow(),
            "issuer": payload.get("iss"),
            "audience": payload.get("aud")
        }
    except jwt.ExpiredSignatureError:
        return {
            "valid": False,
            "error": "Token has expired",
            "expired_at": datetime.fromtimestamp(jwt.decode(token, options={"verify_signature": False})["exp"])
        }
    except jwt.InvalidTokenError as e:
        return {
            "valid": False,
            "error": f"Invalid token: {str(e)}"
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"Error verifying token: {str(e)}"
        }


def format_env_vars(token: str, tenant_id: str) -> str:
    """
    Formate les variables d'environnement pour l'export
    
    Args:
        token: Token JWT
        tenant_id: Identifiant du tenant
    
    Returns:
        Chaîne formatée pour export dans .env ou shell
    """
    return f"""# Variables d'environnement pour dazno.de API MCP
# Générées le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

DAZNO_JWT_TOKEN={token}
DAZNO_TENANT_ID={tenant_id}
"""


def print_token_info(token: str, tenant_id: str, user_id: str, expires_at: datetime):
    """Affiche les informations du token de manière formatée"""
    print("=" * 80)
    print("🔑 TOKEN JWT POUR DAZNO.DE - API MCP")
    print("=" * 80)
    print(f"\n👤 User ID:     {user_id}")
    print(f"🏢 Tenant ID:   {tenant_id}")
    print(f"⏰ Expire dans: {expires_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"🔐 Algorithme:  {JWT_ALGORITHM}")
    print(f"📍 Issuer:      {JWT_ISSUER}")
    print(f"🎯 Audience:    {JWT_AUDIENCE}")
    print("\n" + "-" * 80)
    print("📋 VARIABLES D'ENVIRONNEMENT:")
    print("-" * 80)
    print(format_env_vars(token, tenant_id))
    print("-" * 80)
    print("\n💡 Utilisation:")
    print(f"   curl -H 'Authorization: Bearer {token[:50]}...' \\")
    print(f"        https://api.dazno.de/api/v1/nodes/")
    print("\n" + "=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Génère des tokens JWT pour l'API MCP dazno.de",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Générer un token avec user_id et tenant_id
  python generate_dazno_token.py --user-id dazno_user_001 --tenant-id dazno_tenant_001
  
  # Générer un token avec expiration personnalisée (48 heures)
  python generate_dazno_token.py --user-id dazno_user_001 --tenant-id dazno_tenant_001 --expire-hours 48
  
  # Vérifier un token existant
  python generate_dazno_token.py --verify eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
        """
    )
    
    parser.add_argument(
        "--user-id",
        type=str,
        help="Identifiant de l'utilisateur (sub dans le JWT)"
    )
    
    parser.add_argument(
        "--tenant-id",
        type=str,
        help="Identifiant du tenant (pour isolation des données)"
    )
    
    parser.add_argument(
        "--expire-hours",
        type=int,
        default=DEFAULT_EXPIRATION_HOURS,
        help=f"Nombre d'heures avant expiration (défaut: {DEFAULT_EXPIRATION_HOURS})"
    )
    
    parser.add_argument(
        "--permissions",
        nargs="+",
        default=["read", "write"],
        help="Liste des permissions (défaut: read write)"
    )
    
    parser.add_argument(
        "--verify",
        type=str,
        help="Token JWT à vérifier"
    )
    
    parser.add_argument(
        "--output-env",
        action="store_true",
        help="Afficher uniquement les variables d'environnement (pour export)"
    )
    
    args = parser.parse_args()
    
    # Mode vérification
    if args.verify:
        print("=" * 80)
        print("🔍 VÉRIFICATION DU TOKEN JWT")
        print("=" * 80)
        result = verify_token(args.verify)
        
        if result["valid"]:
            print("\n✅ Token VALIDE")
            print(f"\n👤 User ID:     {result['user_id']}")
            print(f"🏢 Tenant ID:   {result['tenant_id']}")
            print(f"🔐 Permissions: {', '.join(result['permissions'])}")
            print(f"📅 Issued At:   {result['issued_at'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"⏰ Expires At:  {result['expires_at'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            if result["is_expired"]:
                print("\n⚠️  ATTENTION: Le token est EXPIRÉ")
            else:
                remaining = result["expires_at"] - datetime.utcnow()
                print(f"⏳ Temps restant: {remaining}")
            
            print(f"\n📍 Issuer:  {result['issuer']}")
            print(f"🎯 Audience: {result['audience']}")
        else:
            print("\n❌ Token INVALIDE")
            print(f"Erreur: {result.get('error', 'Unknown error')}")
            if 'expired_at' in result:
                print(f"Expiré le: {result['expired_at'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        print("\n" + "=" * 80)
        return
    
    # Mode génération
    if not args.user_id or not args.tenant_id:
        parser.error("--user-id et --tenant-id sont requis pour générer un token")
    
    # Générer le token
    expires_at = datetime.utcnow() + timedelta(hours=args.expire_hours)
    token = create_dazno_jwt_token(
        user_id=args.user_id,
        tenant_id=args.tenant_id,
        permissions=args.permissions,
        expire_hours=args.expire_hours
    )
    
    # Afficher les résultats
    if args.output_env:
        # Mode silencieux pour export dans .env
        print(format_env_vars(token, args.tenant_id).strip())
    else:
        # Mode interactif avec toutes les informations
        print_token_info(token, args.tenant_id, args.user_id, expires_at)
        
        # Vérification optionnelle
        print("\n🔍 Vérification du token généré...")
        verify_result = verify_token(token)
        if verify_result["valid"]:
            print("✅ Token généré et vérifié avec succès!")
        else:
            print(f"❌ Erreur lors de la vérification: {verify_result.get('error')}")
            sys.exit(1)


if __name__ == "__main__":
    main()

