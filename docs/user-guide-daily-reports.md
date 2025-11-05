# Guide Utilisateur : Rapports Quotidiens Automatisés

> **Dernière mise à jour** : 5 novembre 2025  
> **Version** : 1.0.0

## 📋 Table des matières

1. [Introduction](#introduction)
2. [Prérequis](#prérequis)
3. [Activation des rapports quotidiens](#activation)
4. [Consultation des rapports](#consultation)
5. [Comprendre votre rapport](#comprendre)
6. [FAQ](#faq)
7. [Dépannage](#dépannage)

---

## 🎯 Introduction

Les **Rapports Quotidiens Automatisés** vous permettent de recevoir chaque jour une analyse complète et détaillée de votre nœud Lightning Network, sans aucune intervention manuelle.

### Avantages

- ✅ **Analyse automatique** : Votre nœud est analysé chaque jour à 06:00 UTC
- ✅ **Recommandations intelligentes** : Suggestions d'optimisation basées sur l'IA
- ✅ **Historique complet** : Accès à 90 jours d'historique de rapports
- ✅ **Alertes proactives** : Détection automatique des anomalies
- ✅ **Tendances visuelles** : Évolution sur 7 jours de vos métriques clés

---

## 🔑 Prérequis

Avant d'activer les rapports quotidiens, assurez-vous d'avoir :

1. **Un compte DazNode** : Inscrivez-vous sur [dazno.de](https://dazno.de)
2. **Votre clé publique Lightning** : La pubkey de votre nœud (66 caractères hexadécimaux)
3. **Profil complété** : Renseignez votre pubkey dans votre profil utilisateur

### Comment trouver votre pubkey ?

```bash
# Avec LND
lncli getinfo | grep identity_pubkey

# Avec Core Lightning
lightning-cli getinfo | grep id

# Via LNBits
# Allez dans Extensions > LNbits Wallet > Node Info
```

---

## ⚡ Activation des rapports quotidiens {#activation}

### Via l'interface web (dazno.de)

1. **Connectez-vous** à votre compte sur [dazno.de](https://dazno.de)
2. Allez dans **Mon Profil** > **Configuration**
3. Section **Rapports Automatiques**
4. Renseignez votre **pubkey Lightning** si ce n'est pas déjà fait
5. Activez **"Rapport quotidien automatique"**
6. Cliquez sur **Sauvegarder**

✅ **Votre premier rapport sera généré le lendemain à 06:00 UTC.**

### Via l'API

```bash
# Activer les rapports quotidiens
curl -X POST https://api.dazno.de/api/v1/user/profile/daily-report/enable \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json"

# Réponse attendue
{
  "status": "success",
  "message": "Rapport quotidien activé avec succès",
  "next_report": "2025-11-06T06:00:00Z",
  "schedule": "Every day at 06:00 UTC"
}
```

### Vérifier le statut

```bash
# Vérifier le statut du workflow
curl -X GET https://api.dazno.de/api/v1/user/profile/daily-report/status \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Réponse
{
  "enabled": true,
  "schedule": "0 6 * * *",
  "last_report": "2025-11-05T06:00:23Z",
  "total_reports": 15,
  "next_report": "2025-11-06T06:00:00Z"
}
```

---

## 📊 Consultation des rapports {#consultation}

### Via l'interface web

1. Allez dans **Dashboard** > **Rapports Quotidiens**
2. Le **dernier rapport** est affiché automatiquement
3. Utilisez la **timeline** pour accéder aux rapports précédents
4. Cliquez sur **Exporter PDF** pour télécharger un rapport

### Via l'API

#### Récupérer le dernier rapport

```bash
curl -X GET https://api.dazno.de/api/v1/reports/daily/latest \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Récupérer l'historique (30 derniers jours)

```bash
curl -X GET "https://api.dazno.de/api/v1/reports/daily/history?days=30&page=1&limit=10" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Récupérer un rapport spécifique

```bash
curl -X GET https://api.dazno.de/api/v1/reports/daily/{REPORT_ID} \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 📖 Comprendre votre rapport {#comprendre}

Votre rapport quotidien est structuré en plusieurs sections :

### 1. Résumé Exécutif

Le résumé vous donne une vue d'ensemble en un coup d'œil :

```json
{
  "overall_score": 87.5,        // Score global (0-100)
  "score_delta_24h": +2.3,      // Évolution sur 24h
  "status": "healthy",           // healthy / warning / critical
  "critical_alerts": 0,          // Alertes critiques
  "warnings": 2,                 // Avertissements
  "capacity_btc": 5.2,          // Capacité totale
  "channels_count": 45,          // Nombre de canaux
  "forwarding_rate_24h": 0.0023, // Taux de forwards
  "revenue_sats_24h": 12450     // Revenus en satoshis
}
```

#### Interprétation du score

- **90-100** : 🟢 Excellent - Votre nœud est très performant
- **75-89** : 🟡 Bon - Performance satisfaisante avec marge d'amélioration
- **50-74** : 🟠 Moyen - Optimisations recommandées
- **0-49** : 🔴 Faible - Actions correctives nécessaires

#### Statut du nœud

- **healthy** : Tout va bien, aucune action immédiate requise
- **warning** : Attention requise, consulter les recommandations
- **critical** : Action immédiate nécessaire

### 2. Métriques Détaillées

```json
{
  "capacity": {
    "total_sats": 520000000,
    "local_balance": 280000000,   // Liquidité sortante
    "remote_balance": 240000000,  // Liquidité entrante
    "liquidity_ratio": 0.538      // Ratio local/total (optimal: 0.4-0.6)
  },
  "channels": {
    "active": 42,
    "inactive": 3,                 // ⚠️ Canaux à vérifier
    "pending": 0,
    "avg_capacity_sats": 11555555
  },
  "forwarding": {
    "forwards_24h": 156,           // Nombre de forwards
    "forwards_7d": 1089,
    "success_rate_24h": 0.94,      // Taux de succès (optimal: > 0.90)
    "revenue_24h": 12450,          // Revenus en sats
    "revenue_7d": 89230
  },
  "fees": {
    "avg_fee_rate": 250,           // PPM moyen
    "min_fee_rate": 50,
    "max_fee_rate": 2000,
    "base_fee_avg": 1000           // En millisats
  }
}
```

### 3. Recommandations

Les recommandations sont classées par priorité :

```json
{
  "priority": "high",              // high / medium / low
  "category": "liquidity",         // liquidity / fees / channels / performance
  "title": "Rééquilibrage recommandé",
  "description": "3 canaux présentent un déséquilibre > 80%",
  "impact_score": 8.5,            // Impact estimé (0-10)
  "channels_affected": ["chan_1", "chan_2", "chan_3"],
  "suggested_action": "Rebalance 2M sats vers remote",
  "estimated_gain_sats_month": 45000  // Gain estimé par mois
}
```

#### Types de recommandations

- **Liquidity** : Rééquilibrage, ajout de liquidité
- **Fees** : Optimisation des frais
- **Channels** : Ouverture/fermeture de canaux
- **Performance** : Optimisations techniques

### 4. Alertes

Les alertes vous signalent des problèmes nécessitant votre attention :

```json
{
  "severity": "warning",           // critical / warning / info
  "type": "channel_inactive",      // Type d'alerte
  "title": "3 canaux inactifs depuis > 24h",
  "description": "Canaux avec peers: NodeX, NodeY, NodeZ",
  "detected_at": "2025-11-05T02:15:00Z",
  "requires_action": true
}
```

#### Types d'alertes courantes

- **channel_inactive** : Canaux inactifs
- **low_liquidity** : Liquidité insuffisante
- **high_fee_variance** : Écart important dans les frais
- **poor_connectivity** : Problèmes de connectivité
- **stale_channels** : Canaux sans activité

### 5. Tendances (7 jours)

Visualisez l'évolution de vos métriques :

```json
{
  "score_evolution_7d": [82.1, 83.5, 85.2, 84.8, 86.1, 87.0, 87.5],
  "revenue_evolution_7d": [10200, 11800, 13400, 9800, 14200, 12100, 12450],
  "forward_rate_evolution_7d": [0.0019, 0.0021, 0.0024, 0.0018, 0.0026, 0.0022, 0.0023]
}
```

---

## ❓ FAQ {#faq}

### Puis-je modifier l'heure de génération ?

Actuellement, l'heure est fixée à **06:00 UTC** pour tous les utilisateurs (optimisation des ressources serveur). Une personnalisation pourra être ajoutée pour les comptes premium en v2.

### Combien de temps sont conservés les rapports ?

Les rapports sont conservés pendant **90 jours** puis automatiquement supprimés. Vous pouvez exporter vos rapports en PDF pour les conserver plus longtemps.

### Que se passe-t-il si mon nœud est offline ?

Si votre nœud est temporairement offline, le système utilisera les dernières données disponibles et signalera cette situation dans le rapport. Le rapport sera tout de même généré.

### Comment désactiver les rapports quotidiens ?

```bash
# Via API
curl -X POST https://api.dazno.de/api/v1/user/profile/daily-report/disable \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

Ou via l'interface web : **Mon Profil** > **Configuration** > Désactiver "Rapport quotidien automatique"

### Les rapports consomment-ils des ressources de mon nœud ?

Non, l'analyse est effectuée côté serveur DazNode à partir de données publiques (Amboss, Mempool) et ne nécessite aucune connexion directe à votre nœud.

### Puis-je recevoir des notifications ?

Oui ! Vous pouvez configurer des notifications par email ou webhook dans **Mon Profil** > **Notifications**. Cette fonctionnalité sera disponible dans une prochaine mise à jour.

---

## 🔧 Dépannage {#dépannage}

### "Aucun rapport disponible"

**Causes possibles** :
- Vous n'avez pas encore activé les rapports quotidiens
- Votre pubkey n'est pas renseignée dans votre profil
- Le premier rapport n'a pas encore été généré (attendre le lendemain 06:00 UTC)

**Solution** :
1. Vérifiez que votre pubkey est correcte
2. Activez les rapports quotidiens
3. Attendez le lendemain matin

### "User profile not found"

**Cause** : Votre profil n'est pas encore créé dans la base de données.

**Solution** :
1. Complétez votre profil sur dazno.de
2. Renseignez votre pubkey Lightning
3. Sauvegardez les modifications

### "Lightning pubkey required"

**Cause** : Votre pubkey n'est pas renseignée dans votre profil.

**Solution** :
1. Récupérez votre pubkey (voir [Prérequis](#prérequis))
2. Ajoutez-la dans **Mon Profil** > **Node Information**

### Rapport incomplet ou avec erreurs

**Causes possibles** :
- Sources de données temporairement indisponibles (Amboss, Mempool)
- Nœud récemment créé (pas assez d'historique)

**Solution** :
- Le système réessaiera automatiquement
- Consultez le rapport le lendemain
- Contactez support@dazno.de si le problème persiste

---

## 📞 Support

### Besoin d'aide ?

- **Email** : support@dazno.de
- **Discord** : [discord.gg/daznode](https://discord.gg/daznode)
- **Documentation API** : [docs.dazno.de](https://docs.dazno.de)

### Signaler un bug

Si vous rencontrez un problème, incluez les informations suivantes :
- Votre user ID (trouvable dans votre profil)
- Le report ID concerné (si applicable)
- Description du problème
- Captures d'écran si pertinent

---

## 🚀 Roadmap

### Version 1.1 (Q1 2026)
- [ ] Notifications par email/Telegram/Discord
- [ ] Personnalisation de l'heure de génération
- [ ] Rapports hebdomadaires/mensuels
- [ ] Comparaison avec peers similaires

### Version 1.2 (Q2 2026)
- [ ] Export vers Google Sheets/Excel
- [ ] Webhooks personnalisés
- [ ] Alertes temps réel
- [ ] Dashboard interactif avancé

---

**Dernière mise à jour** : 5 novembre 2025  
**Version du guide** : 1.0.0  
**Auteur** : MCP Team

