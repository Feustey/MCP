# Client LNBits Unifié

*Dernière mise à jour: 13 mai 2025*

Ce document décrit l'utilisation du client LNBits unifié, qui fournit une interface standardisée pour interagir avec l'API LNBits.

## Architecture

Le client LNBits unifié est organisé en trois niveaux :

1. **LNBitsBaseClient** : Client de base avec gestion d'authentification, de retry et d'erreurs
2. **LNBitsClient** : Client principal pour les opérations de wallet (invoices, paiements)
3. **LNBitsChannelClient** : Client spécialisé pour la gestion des canaux et des frais

Cette architecture modulaire permet de n'utiliser que les fonctionnalités nécessaires tout en partageant la logique commune.

## Initialisation

```python
from src.unified_clients import LNBitsClient, LNBitsChannelClient

# Client principal pour les opérations de wallet
client = LNBitsClient(
    url="https://your-lnbits-instance.com",
    invoice_key="your_invoice_key",
    admin_key="your_admin_key"
)

# Client pour la gestion des canaux
channel_client = LNBitsChannelClient(
    url="https://your-lnbits-instance.com",
    admin_key="your_admin_key"  # Nécessite uniquement la clé admin
)
```

## Opérations de Wallet

### Vérifier le solde

```python
# Récupérer les détails du wallet
wallet_info = await client.get_wallet_details()
print(f"ID: {wallet_info.id}, Nom: {wallet_info.name}, Solde: {wallet_info.balance} sats")

# Récupérer uniquement le solde
balance = await client.get_balance()
print(f"Solde: {balance} sats")
```

### Créer une facture (invoice)

```python
# Créer une facture de 1000 sats avec une description
invoice = await client.create_invoice(
    amount=1000,
    memo="Paiement pour service XYZ",
    expiry=3600  # Expiration en secondes (1 heure)
)

print(f"Facture créée: {invoice.payment_request}")
print(f"Hash de paiement: {invoice.payment_hash}")
```

### Payer une facture

```python
# Payer une facture BOLT11
payment = await client.pay_invoice(
    bolt11="lnbc10m1p3hum9dpp5...",
    fee_limit_msat=5000  # Limite de frais optionnelle
)

if payment.success:
    print(f"Paiement réussi! Frais: {payment.fee} sats")
    print(f"Preimage: {payment.preimage}")
else:
    print(f"Échec du paiement: {payment.error_message}")
```

### Vérifier le statut d'une facture

```python
# Vérifier si une facture a été payée
is_paid = await client.check_invoice_status("payment_hash_here")
print(f"Facture payée: {is_paid}")
```

### Récupérer l'historique des paiements

```python
# Récupérer les 10 derniers paiements
payments = await client.get_payments(limit=10)
for payment in payments:
    print(f"Montant: {payment.get('amount')} sats, Date: {payment.get('time')}")
```

## Gestion des Canaux

### Lister les canaux

```python
# Récupérer tous les canaux
all_channels = await channel_client.list_channels()
print(f"Nombre total de canaux: {len(all_channels)}")

# Récupérer uniquement les canaux actifs
active_channels = await channel_client.list_channels(active_only=True)
print(f"Nombre de canaux actifs: {len(active_channels)}")
```

### Récupérer les détails d'un canal

```python
# Récupérer un canal par ID, short_id ou channel_point
channel = await channel_client.get_channel("123x456x1")
if channel:
    print(f"Canal trouvé: {channel.id}")
    print(f"Capacité: {channel.capacity} sats")
    print(f"Balance locale: {channel.local_balance} sats")
    print(f"Balance distante: {channel.remote_balance} sats")
else:
    print("Canal non trouvé")
```

### Mettre à jour la politique de frais d'un canal

```python
from src.unified_clients import ChannelPolicy

# Définir une nouvelle politique de frais
policy = ChannelPolicy(
    base_fee_msat=1000,  # 1 sat de frais de base
    fee_rate_ppm=500,    # 0.05% de frais proportionnels
    time_lock_delta=40,  # Delta de timelock standard
    min_htlc_msat=1000,  # Montant minimum d'un HTLC (1 sat)
    disabled=False       # Canal actif pour le routage
)

# Mettre à jour la politique d'un canal spécifique
success = await channel_client.update_channel_policy(
    channel_point="txid:output_index",
    policy=policy
)

print(f"Mise à jour de la politique: {'Réussie' if success else 'Échouée'}")
```

### Mettre à jour tous les canaux actifs

```python
# Mettre à jour tous les canaux actifs avec les mêmes frais
results = await channel_client.update_all_channel_fees(
    base_fee_msat=1000,
    fee_rate_ppm=500,
    exclude_channels=["txid1:0"]  # Optionnel: canaux à exclure
)

# Afficher les résultats
for channel_point, success in results.items():
    print(f"Canal {channel_point}: {'Réussi' if success else 'Échoué'}")
```

### Récupérer l'historique de forwarding

```python
from datetime import datetime

# Définir la période
today = datetime.now().strftime("%Y-%m-%d")
one_month_ago = datetime.now().replace(month=datetime.now().month-1).strftime("%Y-%m-%d")

# Récupérer l'historique de forwarding
forwarding = await channel_client.get_forwarding_history(
    start_date=one_month_ago,
    end_date=today,
    limit=100
)

# Calculer les frais totaux collectés
total_fees = sum(tx.get('fee', 0) for tx in forwarding)
print(f"Nombre de transactions: {len(forwarding)}")
print(f"Frais totaux collectés: {total_fees} sats")
```

## Gestion des erreurs

Le client utilise un système d'erreurs standardisé avec la classe `LNBitsError` :

```python
from src.unified_clients import LNBitsError

try:
    # Opération LNBits
    result = await client.get_wallet_details()
except LNBitsError as e:
    print(f"Erreur LNBits: {e.message}")
    print(f"Type d'erreur: {e.error_type}")
    print(f"Code de statut: {e.status_code}")
finally:
    # Toujours fermer le client à la fin
    await client.close()
```

## Utilisation comme gestionnaire de contexte

Les clients peuvent être utilisés comme gestionnaires de contexte asynchrones :

```python
async with LNBitsClient(url="...", invoice_key="...", admin_key="...") as client:
    # Les opérations ici
    balance = await client.get_balance()
    print(f"Solde: {balance} sats")
    
# Le client est automatiquement fermé à la sortie du bloc
```

## Exemple complet

Voir le fichier [src/examples/lnbits_client_example.py](../../../src/examples/lnbits_client_example.py) pour un exemple complet d'utilisation des clients LNBits. 