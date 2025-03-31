#!/usr/bin/env python3
from auth.jwt import create_permanent_token

def main():
    """Génère un token permanent pour Dazlng."""
    token = create_permanent_token(
        username="dazlng",
        role="admin",
        expires_years=10
    )
    print("\nToken JWT permanent pour Dazlng :")
    print("=" * 80)
    print(token)
    print("=" * 80)
    print("\nUtilisation avec curl :")
    print("-" * 80)
    print(f'curl -X GET "http://localhost:8002/network-summary" -H "Authorization: Bearer {token}"')
    print("-" * 80)

if __name__ == "__main__":
    main() 