"""
Package des clients unifiés pour l'API LNBits.

Ce package contient les clients standardisés pour interagir avec les différentes API de LNBits.
"""

from src.unified_clients.lnbits_base_client import (
    LNBitsBaseClient,
    LNBitsError,
    LNBitsErrorType,
    RetryConfig,
)

from src.unified_clients.lnbits_client import (
    LNBitsClient,
    InvoiceResponse,
    PaymentResponse,
    WalletInfo,
    ChannelInfo,
)

from src.unified_clients.lnbits_channel_client import (
    LNBitsChannelClient,
    ChannelPolicy,
)

__all__ = [
    # Base client
    "LNBitsBaseClient",
    "LNBitsError",
    "LNBitsErrorType",
    "RetryConfig",
    
    # Main client
    "LNBitsClient",
    "InvoiceResponse",
    "PaymentResponse",
    "WalletInfo",
    "ChannelInfo",
    
    # Channel client
    "LNBitsChannelClient",
    "ChannelPolicy",
] 