class LNBitsClientError(Exception):
    """Exception spécifique pour les erreurs LNBits"""
    pass

async def handle_lnbits_response(self, response: aiohttp.ClientResponse) -> Dict:
    """Gère la réponse de l'API LNBits"""
    if response.status != 200:
        error_data = await response.json()
        error_msg = error_data.get("detail", "Erreur inconnue")
        raise LNBitsClientError(f"Erreur API LNBits ({response.status}): {error_msg}")
    return await response.json()

async def get_lnbits_info(self) -> Dict:
    """Récupère les informations de l'instance LNBits"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.lnbits_url}/api/v1/wallet",
                headers={"X-Api-Key": self.lnbits_api_key}
            ) as response:
                return await self.handle_lnbits_response(response)
    except LNBitsClientError as e:
        logger.error(f"Erreur lors de la récupération des informations LNBits: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la récupération des informations LNBits: {str(e)}")
        raise LNBitsClientError(f"Erreur inattendue: {str(e)}") 