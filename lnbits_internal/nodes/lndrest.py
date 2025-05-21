from typing import Optional
from lnbits_internal.nodes.base import Node

class LndRestNode(Node):
    def __init__(
        self,
        endpoint: str,
        macaroon: str,
        cert: Optional[str] = None,
        admin: bool = False,
        invoice: bool = False,
        readonly: bool = False,
    ):
        super().__init__(
            endpoint=endpoint,
            macaroon=macaroon,
            cert=cert,
            admin=admin,
            invoice=invoice,
            readonly=readonly,
        ) 