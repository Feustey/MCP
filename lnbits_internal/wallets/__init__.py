from __future__ import annotations

import importlib

from lnbits_internal.nodes import set_node_class
from lnbits_internal.settings import settings
from lnbits_internal.wallets.base import Wallet
from .lndgrpc import LndWallet
from .lndrest import LndRestWallet

# Les autres wallets (Alby, Blink, etc.) ne sont pas présents dans ce dossier et sont donc retirés.

def set_funding_source(class_name: str | None = None):
    backend_wallet_class = class_name or settings.lnbits_backend_wallet_class
    funding_source_constructor = getattr(wallets_module, backend_wallet_class)
    global funding_source
    funding_source = funding_source_constructor()
    if funding_source.__node_cls__:
        set_node_class(funding_source.__node_cls__(funding_source))


def get_funding_source() -> Wallet:
    return funding_source


wallets_module = importlib.import_module("lnbits_internal.wallets")
# FakeWallet n'est pas présent, donc on ne l'initialise pas ici
funding_source: Wallet | None = None


__all__ = [
    "LndWallet",
    "LndRestWallet",
    "Wallet",
]
