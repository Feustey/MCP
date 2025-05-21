import asyncio
from uuid import uuid4
from lnbits_internal.core.models.users import Account, UserExtra
from lnbits_internal.core.services.users import create_user_account

async def main():
    # Utilisateur 1 : Daznode
    account1 = Account(
        id=uuid4().hex,
        username="Daznode",
        email=None,
        extra=UserExtra(provider="env")
    )
    user1 = await create_user_account(account=account1, wallet_name="Wallet Daznode")
    print("Utilisateur : Daznode")
    print("  Admin key:", user1.wallets[0].adminkey)
    print("  Invoice key:", user1.wallets[0].inkey)
    print()

    # Utilisateur 2 : contact@dazno.de
    account2 = Account(
        id=uuid4().hex,
        username="contactdaznode",
        email="contact@dazno.de",
        extra=UserExtra(provider="env")
    )
    user2 = await create_user_account(account=account2, wallet_name="Wallet contact@dazno.de")
    print("Utilisateur : contact@dazno.de")
    print("  Admin key:", user2.wallets[0].adminkey)
    print("  Invoice key:", user2.wallets[0].inkey)

if __name__ == "__main__":
    asyncio.run(main()) 