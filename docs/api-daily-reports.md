# API Documentation : Rapports Quotidiens

> **Dernière mise à jour** : 5 novembre 2025  
> **Version API** : 1.0.0  
> **Base URL** : `https://api.dazno.de`

## Table des matières

1. [Authentification](#authentification)
2. [Gestion du workflow](#workflow)
3. [Consultation des rapports](#consultation)
4. [Administration](#administration)
5. [Modèles de données](#modeles)
6. [Codes d'erreur](#erreurs)
7. [Exemples d'intégration](#exemples)

---

## 🔐 Authentification {#authentification}

Tous les endpoints nécessitent un **JWT Bearer token** dans le header Authorization.

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Obtenir un token JWT

```bash
curl -X POST https://api.dazno.de/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'
```

---

## ⚙️ Gestion du workflow {#workflow}

### Activer le workflow

**Endpoint** : `POST /api/v1/user/profile/daily-report/enable`

Active la génération automatique de rapports quotidiens pour l'utilisateur authentifié.

#### Requête

```http
POST /api/v1/user/profile/daily-report/enable HTTP/1.1
Host: api.dazno.de
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json
```

#### Réponse

```json
{
  "status": "success",
  "message": "Rapport quotidien activé avec succès",
  "next_report": "2025-11-06T06:00:00Z",
  "schedule": "Every day at 06:00 UTC"
}
```

#### Codes de réponse

- `200 OK` : Workflow activé avec succès
- `400 Bad Request` : Pubkey Lightning manquante
- `404 Not Found` : Profil utilisateur introuvable
- `401 Unauthorized` : Token JWT invalide ou expiré
- `500 Internal Server Error` : Erreur serveur

---

### Désactiver le workflow

**Endpoint** : `POST /api/v1/user/profile/daily-report/disable`

Désactive la génération automatique de rapports quotidiens.

#### Requête

```http
POST /api/v1/user/profile/daily-report/disable HTTP/1.1
Host: api.dazno.de
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json
```

#### Réponse

```json
{
  "status": "success",
  "message": "Rapport quotidien désactivé"
}
```

---

### Obtenir le statut du workflow

**Endpoint** : `GET /api/v1/user/profile/daily-report/status`

Récupère le statut actuel du workflow pour l'utilisateur.

#### Requête

```http
GET /api/v1/user/profile/daily-report/status HTTP/1.1
Host: api.dazno.de
Authorization: Bearer YOUR_JWT_TOKEN
```

#### Réponse

```json
{
  "enabled": true,
  "schedule": "0 6 * * *",
  "last_report": "2025-11-05T06:00:23Z",
  "total_reports": 15,
  "next_report": "2025-11-06T06:00:00Z"
}
```

#### Champs de réponse

| Champ | Type | Description |
|-------|------|-------------|
| `enabled` | boolean | Workflow activé ou non |
| `schedule` | string | Expression cron du planning |
| `last_report` | datetime | Date du dernier rapport généré |
| `total_reports` | integer | Nombre total de rapports générés |
| `next_report` | datetime | Date de la prochaine génération |

---

## 📊 Consultation des rapports {#consultation}

### Récupérer le dernier rapport

**Endpoint** : `GET /api/v1/reports/daily/latest`

Récupère le dernier rapport quotidien généré avec succès.

#### Requête

```http
GET /api/v1/reports/daily/latest HTTP/1.1
Host: api.dazno.de
Authorization: Bearer YOUR_JWT_TOKEN
```

#### Réponse

```json
{
  "status": "success",
  "report": {
    "report_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "user_123",
    "node_pubkey": "02abc...def",
    "node_alias": "MyAwesomeNode",
    "report_date": "2025-11-05T00:00:00Z",
    "generation_timestamp": "2025-11-05T06:00:23Z",
    "report_version": "1.0.0",
    
    "summary": {
      "overall_score": 87.5,
      "score_delta_24h": 2.3,
      "status": "healthy",
      "critical_alerts": 0,
      "warnings": 2,
      "capacity_btc": 5.2,
      "channels_count": 45,
      "forwarding_rate_24h": 0.0023,
      "revenue_sats_24h": 12450
    },
    
    "metrics": {
      "capacity": { /* ... */ },
      "channels": { /* ... */ },
      "forwarding": { /* ... */ },
      "fees": { /* ... */ },
      "network": { /* ... */ }
    },
    
    "recommendations": [ /* ... */ ],
    "alerts": [ /* ... */ ],
    "trends": { /* ... */ },
    
    "rag_asset_id": "daily_report_user123_20251105",
    "rag_indexed": true,
    "generation_status": "completed"
  }
}
```

#### Codes de réponse

- `200 OK` : Rapport récupéré avec succès
- `404 Not Found` : Aucun rapport disponible
- `401 Unauthorized` : Token JWT invalide

---

### Récupérer l'historique des rapports

**Endpoint** : `GET /api/v1/reports/daily/history`

Récupère l'historique paginé des rapports quotidiens.

#### Paramètres de requête

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `days` | integer | 30 | Nombre de jours d'historique (1-90) |
| `page` | integer | 1 | Numéro de page |
| `limit` | integer | 10 | Résultats par page (1-100) |

#### Requête

```http
GET /api/v1/reports/daily/history?days=30&page=1&limit=10 HTTP/1.1
Host: api.dazno.de
Authorization: Bearer YOUR_JWT_TOKEN
```

#### Réponse

```json
{
  "status": "success",
  "reports": [
    {
      "report_id": "...",
      "report_date": "2025-11-05T00:00:00Z",
      "summary": { /* ... */ }
    },
    {
      "report_id": "...",
      "report_date": "2025-11-04T00:00:00Z",
      "summary": { /* ... */ }
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 30,
    "pages": 3
  }
}
```

---

### Récupérer un rapport spécifique

**Endpoint** : `GET /api/v1/reports/daily/{report_id}`

Récupère un rapport spécifique par son ID.

#### Paramètres de chemin

| Paramètre | Type | Description |
|-----------|------|-------------|
| `report_id` | string (UUID) | ID du rapport |

#### Requête

```http
GET /api/v1/reports/daily/550e8400-e29b-41d4-a716-446655440000 HTTP/1.1
Host: api.dazno.de
Authorization: Bearer YOUR_JWT_TOKEN
```

#### Réponse

```json
{
  "status": "success",
  "report": { /* Rapport complet */ }
}
```

#### Codes de réponse

- `200 OK` : Rapport récupéré
- `404 Not Found` : Rapport introuvable
- `401 Unauthorized` : Non autorisé
- `403 Forbidden` : Accès refusé (rapport d'un autre utilisateur)

---

## 🔧 Administration {#administration}

### Déclencher la génération manuelle

**Endpoint** : `POST /api/v1/admin/reports/daily/trigger`

**Permissions** : Administrateur uniquement

Déclenche manuellement la génération de rapports quotidiens.

#### Corps de requête (optionnel)

```json
{
  "user_ids": ["user_123", "user_456"]  // null = tous les users
}
```

#### Requête

```http
POST /api/v1/admin/reports/daily/trigger HTTP/1.1
Host: api.dazno.de
Authorization: Bearer ADMIN_JWT_TOKEN
Content-Type: application/json

{
  "user_ids": null
}
```

#### Réponse

```json
{
  "status": "started",
  "task_id": "daily_reports_20251105_143022",
  "message": "Génération des rapports démarrée en arrière-plan",
  "user_ids": "all"
}
```

---

### Statistiques globales

**Endpoint** : `GET /api/v1/admin/reports/daily/stats`

**Permissions** : Administrateur uniquement

Récupère les statistiques globales sur les rapports quotidiens.

#### Requête

```http
GET /api/v1/admin/reports/daily/stats HTTP/1.1
Host: api.dazno.de
Authorization: Bearer ADMIN_JWT_TOKEN
```

#### Réponse

```json
{
  "status": "success",
  "stats": {
    "users_with_workflow_enabled": 1247,
    "total_reports_generated": 18705,
    "reports_generated_today": 1247,
    "reports_failed_today": 3,
    "success_rate_today": 99.76,
    "timestamp": "2025-11-05T14:30:22Z"
  }
}
```

---

## 📐 Modèles de données {#modeles}

### UserProfile

```typescript
interface UserProfile {
  id: string;
  email: string;
  username: string;
  lightning_pubkey?: string;           // 66 chars hex
  node_alias?: string;
  daily_report_enabled: boolean;
  daily_report_schedule: string;       // Cron expression
  notification_preferences: object;
  last_report_generated?: datetime;
  total_reports_generated: number;
  created_at: datetime;
  updated_at: datetime;
  tenant_id: string;
}
```

### DailyReport

```typescript
interface DailyReport {
  report_id: string;                   // UUID
  user_id: string;
  node_pubkey: string;
  node_alias?: string;
  report_date: datetime;
  generation_timestamp: datetime;
  report_version: string;
  
  summary: ReportSummary;
  metrics: ReportMetrics;
  recommendations: ReportRecommendation[];
  alerts: ReportAlert[];
  trends: ReportTrends;
  
  rag_asset_id?: string;
  rag_indexed: boolean;
  generation_status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message?: string;
  retry_count: number;
  
  created_at: datetime;
  updated_at: datetime;
  tenant_id: string;
}
```

### ReportSummary

```typescript
interface ReportSummary {
  overall_score: number;               // 0-100
  score_delta_24h: number;
  status: 'healthy' | 'warning' | 'critical';
  critical_alerts: number;
  warnings: number;
  capacity_btc: number;
  channels_count: number;
  forwarding_rate_24h: number;
  revenue_sats_24h: number;
}
```

### ReportRecommendation

```typescript
interface ReportRecommendation {
  priority: 'high' | 'medium' | 'low';
  category: 'liquidity' | 'fees' | 'channels' | 'performance';
  title: string;
  description: string;
  impact_score: number;                // 0-10
  channels_affected: string[];
  suggested_action: string;
  estimated_gain_sats_month?: number;
}
```

### ReportAlert

```typescript
interface ReportAlert {
  severity: 'critical' | 'warning' | 'info';
  type: string;                        // channel_inactive, low_liquidity, etc.
  title: string;
  description: string;
  detected_at: datetime;
  requires_action: boolean;
}
```

---

## ⚠️ Codes d'erreur {#erreurs}

| Code | Message | Description |
|------|---------|-------------|
| `400` | Bad Request | Requête invalide (paramètres manquants/incorrects) |
| `401` | Unauthorized | Token JWT invalide ou expiré |
| `403` | Forbidden | Permissions insuffisantes |
| `404` | Not Found | Ressource introuvable |
| `409` | Conflict | Conflit (ex: workflow déjà activé) |
| `429` | Too Many Requests | Rate limit dépassé |
| `500` | Internal Server Error | Erreur serveur |
| `503` | Service Unavailable | Service temporairement indisponible |

### Format d'erreur

```json
{
  "detail": "User profile not found. Please create your profile first.",
  "status_code": 404,
  "timestamp": "2025-11-05T14:30:22Z",
  "request_id": "req_abc123"
}
```

---

## 💡 Exemples d'intégration {#exemples}

### Python avec requests

```python
import requests
from datetime import datetime

class DazNodeClient:
    def __init__(self, api_key):
        self.base_url = "https://api.dazno.de"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def enable_daily_reports(self):
        """Active les rapports quotidiens"""
        response = requests.post(
            f"{self.base_url}/api/v1/user/profile/daily-report/enable",
            headers=self.headers
        )
        return response.json()
    
    def get_latest_report(self):
        """Récupère le dernier rapport"""
        response = requests.get(
            f"{self.base_url}/api/v1/reports/daily/latest",
            headers=self.headers
        )
        return response.json()
    
    def get_report_history(self, days=30, page=1, limit=10):
        """Récupère l'historique des rapports"""
        params = {
            "days": days,
            "page": page,
            "limit": limit
        }
        response = requests.get(
            f"{self.base_url}/api/v1/reports/daily/history",
            headers=self.headers,
            params=params
        )
        return response.json()

# Utilisation
client = DazNodeClient(api_key="your_jwt_token")

# Activer les rapports
result = client.enable_daily_reports()
print(f"Workflow enabled: {result['message']}")

# Récupérer le dernier rapport
report = client.get_latest_report()
print(f"Score: {report['report']['summary']['overall_score']}")

# Récupérer l'historique
history = client.get_report_history(days=7)
print(f"Total reports: {history['pagination']['total']}")
```

### JavaScript/Node.js avec axios

```javascript
const axios = require('axios');

class DazNodeClient {
  constructor(apiKey) {
    this.baseURL = 'https://api.dazno.de';
    this.headers = {
      'Authorization': `Bearer ${apiKey}`,
      'Content-Type': 'application/json'
    };
  }
  
  async enableDailyReports() {
    const response = await axios.post(
      `${this.baseURL}/api/v1/user/profile/daily-report/enable`,
      {},
      { headers: this.headers }
    );
    return response.data;
  }
  
  async getLatestReport() {
    const response = await axios.get(
      `${this.baseURL}/api/v1/reports/daily/latest`,
      { headers: this.headers }
    );
    return response.data;
  }
  
  async getReportHistory(days = 30, page = 1, limit = 10) {
    const response = await axios.get(
      `${this.baseURL}/api/v1/reports/daily/history`,
      {
        headers: this.headers,
        params: { days, page, limit }
      }
    );
    return response.data;
  }
}

// Utilisation
(async () => {
  const client = new DazNodeClient('your_jwt_token');
  
  // Activer les rapports
  const result = await client.enableDailyReports();
  console.log(`Next report: ${result.next_report}`);
  
  // Récupérer le dernier rapport
  const report = await client.getLatestReport();
  console.log(`Status: ${report.report.summary.status}`);
})();
```

### curl

```bash
#!/bin/bash

API_KEY="your_jwt_token"
BASE_URL="https://api.dazno.de"

# Activer les rapports quotidiens
curl -X POST "${BASE_URL}/api/v1/user/profile/daily-report/enable" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json"

# Récupérer le dernier rapport
curl -X GET "${BASE_URL}/api/v1/reports/daily/latest" \
  -H "Authorization: Bearer ${API_KEY}" | jq '.report.summary'

# Récupérer l'historique (7 derniers jours)
curl -X GET "${BASE_URL}/api/v1/reports/daily/history?days=7&limit=7" \
  -H "Authorization: Bearer ${API_KEY}" | jq '.reports[] | {date: .report_date, score: .summary.overall_score}'
```

---

## 📞 Support

- **Documentation** : [docs.dazno.de](https://docs.dazno.de)
- **Email** : api-support@dazno.de
- **Discord** : [discord.gg/daznode](https://discord.gg/daznode)

---

**Version API** : 1.0.0  
**Dernière mise à jour** : 5 novembre 2025  
**Auteur** : MCP Team

