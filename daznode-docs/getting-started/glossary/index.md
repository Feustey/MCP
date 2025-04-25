# Glossaire

Ce glossaire contient les définitions des termes techniques utilisés dans la documentation de Daznode et dans l'écosystème Lightning Network.

## A

### Adresse Lightning
Format username@domain (par exemple, utilisateur@dazno.de) permettant de recevoir facilement des paiements Lightning sans avoir à générer manuellement des factures.

### AMP (Atomic Multi-Path)
Technique permettant de fractionner un paiement Lightning en plusieurs parties pouvant être envoyées par différents chemins, puis rassemblées de manière atomique (tout ou rien) à destination.

### Authentification à deux facteurs (2FA)
Méthode de sécurité qui nécessite deux formes d'identification distinctes pour accéder à un compte. Dans Daznode, la 2FA est obligatoire pour les comptes avec un solde supérieur à 100 000 satoshis.

## B

### Bitcoin Core
Implémentation de référence du protocole Bitcoin. Daznode interagit avec Bitcoin Core pour effectuer des transactions on-chain.

### BTC
Unité de compte principale de Bitcoin. 1 BTC = 100 000 000 satoshis.

## C

### Canal Lightning
Connexion bidirectionnelle entre deux nœuds Lightning qui permet d'effectuer des transactions instantanées sans avoir à les enregistrer sur la blockchain Bitcoin.

### Capacité de canal
Montant total de bitcoins verrouillés dans un canal Lightning. Détermine la quantité maximale qui peut être transférée dans ce canal.

### Capacité entrante
Portion de la capacité d'un canal qui peut être reçue par votre nœud. Nécessaire pour recevoir des paiements Lightning.

### Capacité sortante
Portion de la capacité d'un canal que votre nœud peut envoyer. Nécessaire pour effectuer des paiements Lightning.

## F

### Facture Lightning (Invoice)
Document électronique contenant toutes les informations nécessaires pour effectuer un paiement Lightning, y compris le montant, le destinataire et une preuve cryptographique.

### Fermeture coopérative
Méthode de fermeture d'un canal Lightning où les deux parties collaborent. Plus rapide et moins coûteuse qu'une fermeture forcée.

### Fermeture forcée
Méthode de fermeture d'un canal Lightning utilisée lorsque le nœud distant est inaccessible. Plus coûteuse et implique un délai d'attente pour récupérer les fonds.

## H

### HTLC (Hash Time-Locked Contract)
Type de contrat intelligent utilisé par le Lightning Network pour sécuriser les paiements routés à travers plusieurs nœuds.

## L

### Lightning Network
Solution de couche 2 construite sur Bitcoin qui permet d'effectuer des transactions instantanées, à faible coût et évolutives.

### LNURL
Protocole standardisé facilitant l'interaction entre les portefeuilles Lightning et les services/applications.

## M

### MPP (Multi-Path Payment)
Technique permettant de fractionner un paiement Lightning en plusieurs parties pouvant être envoyées par différents chemins.

## N

### Nœud Lightning
Logiciel qui participe au réseau Lightning en créant des canaux et en routant des paiements. Daznode vous fournit un nœud Lightning géré et accessible via navigateur.

### Nostr
Protocole de communication décentralisé et résistant à la censure souvent utilisé avec Lightning Network pour les paiements et les pourboires (zaps).

### Nostr Wallet Connect (NWC)
Protocole permettant de connecter de manière sécurisée un nœud Lightning à des applications et sites web compatibles via le réseau Nostr.

## O

### On-chain
Se réfère aux transactions qui sont directement enregistrées sur la blockchain Bitcoin. L'ouverture et la fermeture des canaux Lightning sont des transactions on-chain.

## R

### Routage
Processus par lequel un paiement Lightning est acheminé à travers plusieurs nœuds du réseau pour atteindre sa destination.

## S

### Satoshi (sat)
La plus petite unité de Bitcoin. 1 BTC = 100 000 000 satoshis.

### Seed phrase (phrase de récupération)
Suite de mots permettant de restaurer l'accès à un portefeuille Bitcoin. Dans Daznode, les sauvegardes sont gérées différemment pour simplifier l'expérience utilisateur.

### Static Channel Backup (SCB)
Méthode de sauvegarde des canaux Lightning permettant de récupérer les fonds en cas de perte d'accès au nœud. Daznode gère automatiquement les SCB pour vous.

## T

### Testnet
Réseau de test Bitcoin permettant d'expérimenter avec de la monnaie sans valeur réelle. Daznode supporte Testnet4 pour l'apprentissage et l'expérimentation.

## Z

### Zap
Terme utilisé dans l'écosystème Nostr pour désigner un pourboire en satoshis envoyé via le Lightning Network à l'auteur d'une publication. 