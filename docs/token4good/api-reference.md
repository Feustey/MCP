# 📚 Token4Good API Reference

## 🔗 Base URL
```
https://api.dazno.de/api/v1/token4good
```

## 🔐 Authentication
Les endpoints T4G utilisent l'authentification JWT standard de l'API DazNode.

```bash
Authorization: Bearer <your-jwt-token>
```

---

## 👥 Endpoints Utilisateurs

### POST `/users`
Crée un nouveau profil utilisateur T4G.

**Request Body:**
```json
{
  "user_id": "string",
  "username": "string",
  "email": "string",
  "skills": ["string"] // optionnel
}
```

**Response:**
```json
{
  "user_id": "user123",
  "username": "john_doe",
  "email": "john@example.com",
  "total_tokens_earned": 50,
  "total_tokens_spent": 0,
  "current_balance": 50,
  "user_level": "contributeur",
  "skills": ["lightning-network", "bitcoin"],
  "reputation_score": 0.5,
  "created_at": "2025-01-10T10:00:00Z"
}
```

### GET `/users/{user_id}`
Récupère le profil d'un utilisateur.

**Response:**
```json
{
  "user_id": "user123",
  "username": "john_doe",
  "total_tokens_earned": 150,
  "current_balance": 85,
  "user_level": "contributeur",
  "reputation_score": 0.7,
  "last_activity": "2025-01-10T15:30:00Z"
}
```

### GET `/users/{user_id}/statistics`
Récupère les statistiques complètes d'un utilisateur.

**Response:**
```json
{
  "profile": { /* UserProfile object */ },
  "total_transactions": 25,
  "mentoring_given": 8,
  "mentoring_received": 3,
  "tokens_by_action": {
    "mentoring": 400,
    "code_review": 240,
    "documentation": 200
  },
  "avg_session_rating": 4.6,
  "community_rank": 15,
  "next_level": {
    "next_level": "MENTOR",
    "tokens_needed": 350,
    "progress_percentage": 30
  }
}
```

### GET `/users/{user_id}/opportunities`
Suggère des opportunités de gains personnalisées.

**Response:**
```json
{
  "opportunities": [
    {
      "type": "mentoring",
      "title": "Commencer le mentoring",
      "description": "Partagez votre expertise Lightning Network",
      "potential_tokens": "50-100 T4G",
      "difficulty": "Facile",
      "time_investment": "1-2h"
    }
  ]
}
```

### GET `/leaderboard`
Récupère le classement communautaire.

**Query Params:**
- `limit` (int): Nombre d'entrées (défaut: 10)

**Response:**
```json
{
  "leaderboard": [
    {
      "rank": 1,
      "username": "lightning_expert",
      "user_level": "expert",
      "total_tokens": 2500,
      "reputation_score": 0.95,
      "mentoring_sessions": 45,
      "skills": ["lightning-network", "bitcoin", "dazbox"]
    }
  ]
}
```

---

## 💰 Endpoints Tokens

### POST `/tokens/award`
Attribue des tokens T4G à un utilisateur.

**Request Body:**
```json
{
  "user_id": "string",
  "action_type": "mentoring|code_review|documentation|support_technique|parrainage",
  "tokens": 50,
  "description": "string",
  "metadata": {}, // optionnel
  "impact_score": 1.0 // optionnel
}
```

**Response:**
```json
{
  "id": "txn_123",
  "user_id": "user123",
  "action_type": "mentoring",
  "tokens_earned": 65, // après multiplieurs
  "description": "Session Lightning Network complétée",
  "timestamp": "2025-01-10T16:00:00Z",
  "impact_score": 1.3
}
```

### GET `/tokens/{user_id}/balance`
Récupère le solde de tokens.

**Response:**
```json
{
  "user_id": "user123",
  "total_earned": 500,
  "total_spent": 150,
  "available_balance": 350,
  "user_level": "mentor"
}
```

### GET `/tokens/{user_id}/transactions`
Récupère l'historique des transactions.

**Query Params:**
- `limit` (int): Nombre de transactions (défaut: 50)

**Response:**
```json
{
  "transactions": [
    {
      "id": "txn_456",
      "action_type": "mentoring",
      "tokens_earned": 75,
      "tokens_spent": 0,
      "description": "Session DazBox setup",
      "timestamp": "2025-01-10T14:30:00Z"
    }
  ],
  "total_count": 25
}
```

---

## 🎓 Endpoints Mentoring

### POST `/mentoring/sessions`
Crée une session de mentoring.

**Request Body:**
```json
{
  "mentor_id": "string",
  "mentee_id": "string",
  "topic": "string",
  "category": "lightning_network|dazbox_setup|business_dev|dazpay_integration",
  "duration_minutes": 60
}
```

**Response:**
```json
{
  "id": "session_123",
  "mentor_id": "mentor456",
  "mentee_id": "mentee789",
  "topic": "Configuration nœud Lightning",
  "category": "lightning_network",
  "duration_minutes": 60,
  "tokens_reward": 50,
  "status": "scheduled",
  "scheduled_at": "2025-01-10T16:00:00Z"
}
```

### POST `/mentoring/sessions/complete`
Finalise une session de mentoring.

**Request Body:**
```json
{
  "session_id": "string",
  "feedback": {
    "rating": 5,
    "comments": "Excellent mentoring, très utile!",
    "learned_skills": ["node-configuration", "channel-management"]
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Session complétée avec succès"
}
```

### GET `/mentoring/sessions/{user_id}`
Récupère les sessions d'un utilisateur.

**Query Params:**
- `as_mentor` (bool): true pour mentor, false pour mentee (défaut: true)

**Response:**
```json
{
  "sessions": [
    {
      "id": "session_123",
      "topic": "DazBox optimization",
      "status": "completed",
      "tokens_reward": 75,
      "feedback": {
        "rating": 5,
        "comments": "Super helpful!"
      },
      "completed_at": "2025-01-10T17:00:00Z"
    }
  ]
}
```

---

## 🛍️ Endpoints Marketplace

### POST `/marketplace/services`
Crée un service dans la marketplace.

**Request Body:**
```json
{
  "provider_id": "string",
  "name": "string",
  "description": "string",
  "category": "technical_excellence|business_growth|knowledge_transfer|community_services",
  "token_cost": 100,
  "estimated_duration": "2h",
  "requirements": ["string"], // optionnel
  "tags": ["string"] // optionnel
}
```

**Response:**
```json
{
  "id": "service_123",
  "name": "Audit Lightning Node",
  "description": "Analyse complète et recommandations",
  "category": "technical_excellence",
  "provider_id": "expert456",
  "token_cost": 150,
  "estimated_duration": "3h",
  "is_active": true,
  "rating": null,
  "total_bookings": 0
}
```

### POST `/marketplace/search`
Recherche des services.

**Request Body:**
```json
{
  "category": "technical_excellence", // optionnel
  "max_cost": 200, // optionnel
  "tags": ["lightning", "optimization"], // optionnel
  "provider_level": "expert" // optionnel
}
```

**Response:**
```json
{
  "services": [
    {
      "id": "service_456",
      "name": "Migration Lightning Node",
      "description": "Migration sécurisée avec backup",
      "token_cost": 180,
      "rating": 4.8,
      "provider_id": "expert789"
    }
  ],
  "count": 5
}
```

### POST `/marketplace/book`
Réserve un service.

**Request Body:**
```json
{
  "client_id": "string",
  "service_id": "string",
  "scheduled_at": "2025-01-15T14:00:00Z", // optionnel
  "notes": "string" // optionnel
}
```

**Response:**
```json
{
  "id": "booking_123",
  "service_id": "service_456",
  "client_id": "client789",
  "provider_id": "provider123",
  "tokens_cost": 180,
  "status": "pending",
  "created_at": "2025-01-10T16:30:00Z"
}
```

### POST `/marketplace/bookings/complete`
Finalise une réservation.

**Request Body:**
```json
{
  "booking_id": "string",
  "feedback": {
    "rating": 5,
    "comments": "Service excellent, très professionnel",
    "would_recommend": true
  }
}
```

### GET `/marketplace/bookings/{user_id}`
Récupère les réservations d'un utilisateur.

**Query Params:**
- `as_client` (bool): true pour client, false pour provider (défaut: true)

**Response:**
```json
{
  "bookings": [
    {
      "id": "booking_456",
      "service_id": "service_123",
      "status": "completed",
      "tokens_cost": 150,
      "completed_at": "2025-01-10T18:00:00Z",
      "feedback": {
        "rating": 5,
        "comments": "Parfait!"
      }
    }
  ]
}
```

### GET `/marketplace/recommendations/{user_id}`
Récupère des recommandations personnalisées.

**Query Params:**
- `limit` (int): Nombre de recommandations (défaut: 5)

**Response:**
```json
{
  "recommendations": [
    {
      "service": {
        "id": "service_789",
        "name": "Formation Lightning avancée",
        "token_cost": 120
      },
      "score": 8.5,
      "reason": "Correspond à vos intérêts: Lightning Network • Service populaire"
    }
  ]
}
```

### GET `/marketplace/stats`
Statistiques de la marketplace.

**Response:**
```json
{
  "total_services": 45,
  "total_bookings": 230,
  "completed_bookings": 195,
  "completion_rate": 0.85,
  "total_volume_tokens": 15400,
  "average_rating": 4.6,
  "top_services": [
    {
      "service": "Support Lightning Network",
      "bookings": 25
    }
  ],
  "active_providers": 18
}
```

---

## 🏆 Endpoints Administratifs

### POST `/admin/rewards/weekly-bonuses`
Déclenche les bonus hebdomadaires.

**Response:**
```json
{
  "bonuses_awarded": [
    {
      "rank": 1,
      "user_id": "user123",
      "weekly_tokens": 450,
      "bonus": 100
    }
  ]
}
```

### GET `/admin/system/status`
Statut du système T4G.

**Response:**
```json
{
  "system_health": "active",
  "total_users": 150,
  "total_transactions": 1250,
  "total_services": 45,
  "total_bookings": 230,
  "level_distribution": {
    "contributeur": 95,
    "mentor": 42,
    "expert": 13
  },
  "token_economy": {
    "total_earned": 45000,
    "total_spent": 28000,
    "in_circulation": 17000
  }
}
```

---

## 📊 Codes de Statut HTTP

| Code | Description |
|------|-------------|
| `200` | Succès |
| `201` | Créé avec succès |
| `400` | Requête invalide |
| `401` | Non authentifié |
| `403` | Accès refusé |
| `404` | Ressource non trouvée |
| `429` | Trop de requêtes |
| `500` | Erreur serveur |

---

## 🔔 Webhooks (Optionnel)

Le système T4G peut envoyer des webhooks pour les événements importants :

### Events Disponibles
- `tokens.awarded` - Tokens attribués
- `level.up` - Changement de niveau
- `achievement.unlocked` - Achievement débloqué
- `session.completed` - Session de mentoring terminée
- `booking.completed` - Service marketplace terminé

### Format Webhook
```json
{
  "event": "tokens.awarded",
  "timestamp": "2025-01-10T16:00:00Z",
  "data": {
    "user_id": "user123",
    "tokens": 75,
    "action_type": "mentoring",
    "description": "Session Lightning Network"
  }
}
```

---

## 🚀 SDK et Intégrations

Des SDKs sont disponibles pour faciliter l'intégration :

- **JavaScript/Node.js** : `npm install @daznode/token4good-sdk`
- **Python** : `pip install daznode-token4good`
- **Go** : `go get github.com/daznode/token4good-go`

### Exemple SDK JavaScript
```javascript
import { T4GClient } from '@daznode/token4good-sdk';

const client = new T4GClient({
  baseUrl: 'https://api.dazno.de',
  token: 'your-jwt-token'
});

// Créer un utilisateur
const user = await client.users.create({
  user_id: 'user123',
  username: 'john_doe',
  email: 'john@example.com',
  skills: ['lightning-network']
});

// Attribuer des tokens
const transaction = await client.tokens.award({
  user_id: 'user123',
  action_type: 'mentoring',
  tokens: 50,
  description: 'Session Lightning Network'
});
```

Cette API reference complète permet d'intégrer facilement le système Token4Good dans vos applications ! 🚀