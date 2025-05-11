# Clients Unifiés pour LNBits

*Dernière mise à jour: 13 mai 2025*

Ce répertoire contient les clients unifiés pour interagir avec l'API LNBits de manière standardisée et robuste.

## Structure

- **lnbits_base_client.py** : Client de base avec gestion d'authentification, de retry et d'erreurs
- **lnbits_client.py** : Client principal pour les opérations de wallet (invoices, paiements)
- **lnbits_channel_client.py** : Client spécialisé pour la gestion des canaux et des frais

## Caractéristiques

- **Gestion d'erreurs standardisée** : Toutes les erreurs sont encapsulées dans la classe `LNBitsError`
- **Mécanisme de retry** : Retente automatiquement les requêtes en cas d'erreur temporaire
- **Logging** : Journalisation détaillée des opérations et des erreurs
- **Modèles de données** : Utilisation de Pydantic pour la validation des données
- **Gestionnaires de contexte** : Utilisation possible comme gestionnaires de contexte asynchrones

## Utilisation

```python
from src.unified_clients import LNBitsClient, LNBitsChannelClient, ChannelPolicy

# Client principal
client = LNBitsClient(
    url="https://your-lnbits-instance.com",
    invoice_key="your_invoice_key",
    admin_key="your_admin_key"
)

# Client pour la gestion des canaux
channel_client = LNBitsChannelClient(
    url="https://your-lnbits-instance.com",
    admin_key="your_admin_key"
)

# Exemple d'utilisation
async def main():
    # Opérations de wallet
    balance = await client.get_balance()
    print(f"Solde: {balance} sats")
    
    # Opérations sur les canaux
    channels = await channel_client.list_channels(active_only=True)
    print(f"Canaux actifs: {len(channels)}")
    
    # Fermeture propre des clients
    await client.close()
    await channel_client.close()
```

Pour une documentation complète, voir [docs/api/lnbits_client.md](../../docs/api/lnbits_client.md).

## Tests

Les tests unitaires pour les clients se trouvent dans `tests/unit/clients/`.

Pour exécuter les tests :

```bash
pytest tests/unit/clients/
``` 