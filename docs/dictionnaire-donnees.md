# Dictionnaire de Données MCP

> Dernière mise à jour: 25 juin 2025

Ce document définit les structures de données standards utilisées dans le système MCP, notamment pour les nœuds, canaux et politiques de frais. Ces définitions sont strictes et non-ambigües pour assurer la cohérence dans tout le système.

## 1. Structure Nœud Lightning

Un nœud Lightning est représenté par la structure suivante:

```json
{
  "node_id": "string", // Clé publique hexadécimale du nœud (66 caractères)
  "alias": "string", // Alias du nœud (max 32 caractères)
  "color": "string", // Couleur hexadécimale (format "#RRGGBB")
  "last_update": "timestamp", // Format ISO8601 (YYYY-MM-DDThh:mm:ss.sssZ)
  "pubkey": "string", // Identique à node_id, pour compatibilité
  "capacity": {
    "total": number, // Capacité totale du nœud en sats
    "channels": number // Nombre total de canaux
  },
  "connectivity": {
    "addresses": [ // Liste des adresses connues du nœud
      {
        "network": "string", // "ipv4", "ipv6", "tor", "websocket"
        "addr": "string" // Format dépendant du réseau
      }
    ],
    "last_seen": "timestamp" // Dernière fois que le nœud a été vu en ligne
  },
  "scores": {
    "availability": number, // 0.0-1.0, taux de disponibilité
    "centrality": number, // 0.0-1.0, mesure de centralité dans le réseau
    "stability": number, // 0.0-1.0, stabilité historique
    "fee_efficiency": number, // 0.0-1.0, efficacité des frais
    "overall": number // 0.0-1.0, score global pondéré
  },
  "channels": [], // Liste des canaux (voir structure Canal ci-dessous)
  "metadata": { // Métadonnées supplémentaires (extensible)
    "location": { // Si connue
      "country": "string",
      "region": "string",
      "provider": "string"
    },
    "version": "string", // Version LND/CLN si connue
    "operator": "string", // Opérateur connu si disponible
    "tags": ["string"] // Tags catégorisant le nœud
  }
}
```

## 2. Structure Canal Lightning

Un canal Lightning est représenté par la structure suivante:

```json
{
  "channel_id": "string", // ID du canal (format: txid:vout ou format court)
  "short_channel_id": "string", // ID court (format: blockheight:txindex:output)
  "capacity": number, // Capacité totale du canal en sats
  "transaction_id": "string", // ID de la transaction d'ouverture (txid)
  "transaction_vout": number, // Index de sortie dans la transaction
  "node1_pub": "string", // Clé publique du nœud 1
  "node2_pub": "string", // Clé publique du nœud 2
  "node1_alias": "string", // Alias du nœud 1 si connu
  "node2_alias": "string", // Alias du nœud 2 si connu
  "created_at": "timestamp", // Date d'ouverture du canal
  "last_update": "timestamp", // Dernière mise à jour du canal
  "status": "string", // "active", "inactive", "closing", "closed"
  "balance": {
    "local": number, // Balance locale en sats (optionnel, confidentiel)
    "remote": number, // Balance distante en sats (optionnel, confidentiel)
    "ratio": number // Ratio local/(local+remote) (0.0-1.0)
  },
  "policies": {
    "node1": { // Politique du nœud 1
      "fee_base_msat": number, // Frais de base en millionièmes de sat
      "fee_rate_milli_msat": number, // Taux de frais en millionièmes de sat
      "min_htlc_msat": number, // Montant minimum HTLC en millionièmes de sat
      "max_htlc_msat": number, // Montant maximum HTLC en millionièmes de sat
      "time_lock_delta": number, // Delta de timelock
      "disabled": boolean // Si la politique est désactivée
    },
    "node2": { /* Même structure que node1 */ }
  },
  "metrics": {
    "forwards_count": number, // Nombre total de forwards
    "forwards_volume_sat": number, // Volume total des forwards en sats
    "success_rate": number, // Taux de réussite des forwards (0.0-1.0)
    "average_htlc_size": number, // Taille moyenne des HTLCs en sats
    "revenue_msat": number, // Revenus générés en millionièmes de sat
    "uptime": number // Uptime en pourcentage (0.0-1.0)
  },
  "metadata": { // Métadonnées supplémentaires
    "is_private": boolean, // Si le canal est privé
    "htlc_maximum_msat": number, // Maximum HTLC en millionièmes de sat
    "peer_features": [], // Fonctionnalités supportées par le pair
    "custom_records": {} // Champs personnalisés
  }
}
```

## 3. Structure Politique de Frais

Une politique de frais est représentée par la structure suivante:

```json
{
  "channel_id": "string", // ID du canal concerné
  "node_id": "string", // Nœud qui applique la politique
  "timestamp": "timestamp", // Date d'application de la politique
  "previous": { // Politique précédente (pour rollback)
    "fee_base_msat": number,
    "fee_rate_milli_msat": number,
    "min_htlc_msat": number,
    "max_htlc_msat": number,
    "time_lock_delta": number,
    "disabled": boolean
  },
  "current": { // Politique actuelle
    "fee_base_msat": number,
    "fee_rate_milli_msat": number,
    "min_htlc_msat": number,
    "max_htlc_msat": number,
    "time_lock_delta": number,
    "disabled": boolean
  },
  "direction": "string", // "incoming" ou "outgoing" selon le sens de la politique
  "reason": "string", // Raison de la modification
  "applied": boolean, // Si la politique a été effectivement appliquée
  "result": "string", // "success", "failure", "pending", "dry_run"
  "metadata": { // Métadonnées supplémentaires
    "optimizer_version": "string", // Version de l'optimiseur utilisé
    "confidence_score": number, // Score de confiance (0.0-1.0)
    "trigger": "string", // Élément déclencheur de la modification
    "rollback_id": "string" // ID pour rollback si nécessaire
  }
}
```

## 4. Structure Décision

Une décision d'optimisation est représentée par la structure suivante:

```json
{
  "decision_id": "string", // UUID unique de la décision
  "timestamp": "timestamp", // Date de la décision
  "node_id": "string", // Nœud concerné
  "channel_id": "string", // Canal concerné (le cas échéant)
  "decision_type": "string", // "NO_ACTION", "INCREASE_FEES", "LOWER_FEES", "CLOSE_CHANNEL", "REBALANCE"
  "confidence": number, // Niveau de confiance (0.0-1.0)
  "scores": { // Scores ayant mené à la décision
    "success_rate": number, // 0.0-1.0
    "activity": number, // 0.0-1.0
    "fee_efficiency": number, // 0.0-1.0
    "liquidity_balance": number, // 0.0-1.0
    "centrality": number, // 0.0-1.0
    "age": number, // 0.0-1.0
    "stability": number, // 0.0-1.0
    "total": number // Score global 0.0-1.0
  },
  "parameters": { // Paramètres de la décision
    "fee_adjustment": number, // % d'ajustement des frais
    "min_confidence_threshold": number, // Seuil min de confiance
    "max_adjustment_limit": number, // Limite max d'ajustement
    "consider_historical_data": boolean // Si données historiques considérées
  },
  "details": {
    "reasoning": "string", // Explication de la décision
    "alternative_actions": ["string"], // Actions alternatives considérées
    "data_points_considered": number // Nombre de points de données considérés
  },
  "execution_status": "string", // "pending", "approved", "rejected", "executed", "failed", "rolled_back"
  "execution_timestamp": "timestamp", // Date d'exécution si applicable
  "execution_result": "string", // Résultat détaillé de l'exécution
  "user_override": boolean, // Si un utilisateur a remplacé la décision
  "metadata": {
    "version": "string", // Version du decision engine
    "auto_approved": boolean, // Si auto-approuvé
    "tags": ["string"] // Tags pertinents
  }
}
```

## 5. Structure Donnée RAG

Les données du système RAG sont représentées par la structure suivante:

```json
{
  "id": "string", // ID unique du document
  "content": "string", // Contenu textuel du document
  "source": "string", // Source du document
  "embedding": [number], // Vecteur d'embedding (liste de flottants)
  "metadata": {
    "created_at": "timestamp", // Date de création
    "language": "string", // Langue du document
    "type": "string", // Type de document
    "related_node": "string", // Nœud associé si applicable
    "related_channel": "string", // Canal associé si applicable
    "tags": ["string"], // Tags associés
    "confidence": number, // Score de confiance 0.0-1.0
    "author": "string" // Auteur ou générateur
  }
}
```

## Règles de Validation

1. Tous les champs marqués sans commentaire "optionnel" sont obligatoires
2. Les timestamp doivent être au format ISO8601 (YYYY-MM-DDThh:mm:ss.sssZ)
3. Les ID de nœuds doivent être des clés publiques hexadécimales valides
4. Les scores doivent être dans l'intervalle [0.0, 1.0]
5. Les montants en sats doivent être des entiers non négatifs
6. Les montants en msats doivent être des entiers non négatifs
7. Les champs booléens doivent être true ou false (pas 0/1)
8. Les champs enum (comme decision_type) doivent correspondre aux valeurs définies

Ces structures sont à utiliser de manière stricte dans tous les modules du système MCP pour garantir la cohérence et l'interopérabilité.

## Exemples

Des exemples concrets de ces structures sont disponibles dans les fichiers suivants:
- [data/test/node_example.json](mdc:data/test/node_example.json)
- [data/test/channel_example.json](mdc:data/test/channel_example.json)
- [data/test/fee_policy_example.json](mdc:data/test/fee_policy_example.json)
- [data/test/decision_example.json](mdc:data/test/decision_example.json) 