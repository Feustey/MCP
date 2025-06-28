# 🚀 API.DAZNO.DE - SPÉCIFICATIONS TECHNIQUES V2

## 📋 VUE D'ENSEMBLE

api.dazno.de est le cœur de l'intelligence de l'écosystème DazNode. Cette API doit fournir toutes les fonctionnalités avancées de :
- Yield Finance
- Liquidity Subscriptions
- Marketplace & IA
- LINER Index

## 🏗 ARCHITECTURE GÉNÉRALE

### Format de Réponse Standard
```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: unknown;
  };
  meta: {
    timestamp: string;
    version: string;
    request_id: string;
  };
}
```

### Codes d'Erreur
```typescript
enum ApiErrorCode {
  // Erreurs Client (4xx)
  VALIDATION_ERROR = 'VALIDATION_ERROR',       // 400
  AUTHENTICATION_ERROR = 'AUTH_ERROR',         // 401
  AUTHORIZATION_ERROR = 'FORBIDDEN',           // 403
  NOT_FOUND = 'NOT_FOUND',                    // 404
  RATE_LIMIT_ERROR = 'RATE_LIMIT',            // 429
  
  // Erreurs Serveur (5xx)
  INTERNAL_ERROR = 'INTERNAL_ERROR',          // 500
  SERVICE_UNAVAILABLE = 'SERVICE_UNAVAILABLE', // 503
  
  // Erreurs Métier
  INSUFFICIENT_FUNDS = 'INSUFFICIENT_FUNDS',
  CHANNEL_UNAVAILABLE = 'CHANNEL_UNAVAILABLE',
  STRATEGY_CONFLICT = 'STRATEGY_CONFLICT',
  MARKET_CLOSED = 'MARKET_CLOSED'
}
```

## 📡 ENDPOINTS API

### 1. YIELD FINANCE

#### 1.1 Création de Stratégie
```http
POST /api/v1/yield/strategies
```
```typescript
interface CreateYieldStrategyRequest {
  type: 'liquidity_provider' | 'channel_fees' | 'hybrid';
  amount: number;                // en sats
  risk_tolerance: 'low' | 'medium' | 'high';
  timeframe: string;            // ex: '30d'
  constraints?: {
    min_yield?: number;         // pourcentage minimum de rendement
    max_channels?: number;      // nombre maximum de canaux
    min_channel_size?: number;  // taille minimum par canal en sats
    geographical_focus?: string[]; // régions préférées
  };
  auto_compound?: boolean;      // réinvestissement automatique
}

interface YieldStrategy {
  id: string;
  status: 'pending' | 'active' | 'paused' | 'completed';
  created_at: string;
  metrics: {
    current_apy: number;        // APY actuel
    total_yield: number;        // Yield total généré
    risk_score: number;         // Score de risque (0-1)
    efficiency: number;         // Efficacité d'utilisation (0-1)
  };
  performance: {
    daily: YieldPerformance[];  // 24 dernières heures
    weekly: YieldPerformance[]; // 7 derniers jours
    monthly: YieldPerformance[]; // 30 derniers jours
  };
}
```

#### 1.2 Récupération des Performances
```http
GET /api/v1/yield/strategies/{id}/performance
```
```typescript
interface YieldPerformance {
  timestamp: string;
  realized_yield: number;      // Yield réalisé
  unrealized_yield: number;    // Yield non réalisé
  fees_earned: number;         // Frais gagnés
  rebalancing_costs: number;   // Coûts de rebalancement
  efficiency_score: number;    // Score d'efficacité (0-1)
  risk_metrics: {
    volatility: number;
    max_drawdown: number;
    sharpe_ratio: number;
  };
}
```

#### 1.3 Optimisation de Stratégie
```http
POST /api/v1/yield/strategies/{id}/optimize
```
```typescript
interface OptimizeStrategyRequest {
  target: 'yield' | 'risk' | 'balanced';
  constraints?: {
    max_changes?: number;      // Nombre maximum de changements
    max_rebalance?: number;    // Montant maximum de rebalancement
  };
}

interface OptimizationResult {
  recommended_actions: {
    type: 'rebalance' | 'open_channel' | 'close_channel';
    priority: 'high' | 'medium' | 'low';
    expected_impact: {
      yield_increase: number;
      risk_change: number;
    };
    details: Record<string, unknown>;
  }[];
  estimated_improvement: {
    yield_increase: number;
    risk_reduction: number;
  };
}
```

### 2. LIQUIDITY SUBSCRIPTIONS

#### 2.1 Création d'Abonnement
```http
POST /api/v1/liquidity/subscriptions
```
```typescript
interface CreateSubscriptionRequest {
  plan_type: 'starter' | 'professional' | 'enterprise';
  node_pubkey: string;
  amount_limit: number;        // Limite en sats
  optimization_goals: {
    cost_reduction: number;    // Importance (0-1)
    reliability: number;       // Importance (0-1)
    revenue: number;          // Importance (0-1)
  };
  auto_rebalance: boolean;    // Rebalancement automatique
  alert_preferences: {
    email?: string[];
    webhook_url?: string;
    telegram_chat_id?: string;
    thresholds: {
      low_liquidity: number;  // % de capacité
      high_fees: number;      // en sats
      offline_duration: number; // en minutes
    };
  };
}

interface LiquiditySubscription {
  id: string;
  status: 'active' | 'suspended' | 'cancelled';
  metrics: {
    total_capacity: number;
    active_channels: number;
    optimization_score: number;
    reliability_score: number;
    cost_efficiency: number;
  };
  current_actions: SubscriptionAction[];
  recommendations: SubscriptionRecommendation[];
}
```

#### 2.2 Monitoring en Temps Réel
```http
GET /api/v1/liquidity/subscriptions/{id}/monitor
```
```typescript
interface MonitoringUpdate {
  timestamp: string;
  metrics: {
    current_liquidity: number;
    inbound_capacity: number;
    outbound_capacity: number;
    fee_rates: {
      min: number;
      max: number;
      median: number;
    };
    channel_states: {
      active: number;
      inactive: number;
      pending: number;
    };
  };
  alerts: {
    level: 'info' | 'warning' | 'critical';
    type: string;
    message: string;
    details: Record<string, unknown>;
  }[];
}
```

### 3. MARKETPLACE & IA

#### 3.1 Publication d'Annonce
```http
POST /api/v1/marketplace/listings
```
```typescript
interface CreateListingRequest {
  channel_id: string;
  capacity: number;
  asking_price: number;
  terms: {
    min_duration?: string;
    fee_guarantee?: boolean;
    uptime_guarantee?: number;
    cancellation_policy: string;
  };
  preferences?: {
    geographical_region?: string[];
    min_node_age?: string;
    min_capacity?: number;
  };
}

interface ChannelListing {
  id: string;
  status: 'active' | 'pending' | 'sold';
  ai_analysis: {
    fair_price_estimate: number;
    demand_score: number;
    risk_assessment: {
      score: number;
      factors: string[];
    };
    market_fit: {
      score: number;
      matching_criteria: string[];
    };
  };
  market_data: {
    similar_listings: number;
    avg_price: number;
    price_trend: 'increasing' | 'stable' | 'decreasing';
  };
}
```

#### 3.2 Recherche Intelligente
```http
POST /api/v1/marketplace/search
```
```typescript
interface MarketplaceSearch {
  criteria: {
    min_capacity?: number;
    max_price?: number;
    geographical_region?: string[];
    min_reputation?: number;
  };
  preferences?: {
    optimization_target: 'price' | 'reliability' | 'balanced';
    importance_weights: {
      price: number;           // 0-1
      reputation: number;      // 0-1
      location: number;        // 0-1
      capacity: number;        // 0-1
    };
  };
}

interface SearchResults {
  matches: ChannelMatch[];
  ai_insights: {
    market_summary: string;
    price_analysis: string;
    timing_recommendation: string;
  };
  alternative_suggestions: {
    description: string;
    modified_criteria: MarketplaceSearch;
  }[];
}
```

### 4. LINER INDEX

#### 4.1 Index Actuel
```http
GET /api/v1/index/liner/current
```
```typescript
interface LinerIndex {
  timestamp: string;
  value: number;
  components: {
    routing_rates: number;
    channel_yields: number;
    liquidity_premium: number;
  };
  confidence_interval: {
    lower: number;
    upper: number;
  };
  market_conditions: {
    liquidity_score: number;
    volatility: number;
    trend: 'increasing' | 'decreasing' | 'stable';
  };
  predictions: {
    short_term: IndexPrediction; // 24h
    medium_term: IndexPrediction; // 7j
    long_term: IndexPrediction;  // 30j
  };
}
```

#### 4.2 Analyse de Marché
```http
GET /api/v1/index/liner/analysis
```
```typescript
interface MarketAnalysis {
  global_metrics: {
    total_network_liquidity: number;
    active_channels_count: number;
    network_growth_rate: number;
    fee_market_health: number;
  };
  regional_analysis: {
    region: string;
    liquidity_distribution: number;
    fee_rates: {
      min: number;
      max: number;
      median: number;
    };
    growth_metrics: {
      new_channels: number;
      capacity_change: number;
    };
  }[];
  opportunities: {
    type: string;
    description: string;
    expected_roi: number;
    confidence_score: number;
    implementation_complexity: 'low' | 'medium' | 'high';
  }[];
}
```

## 🔒 SÉCURITÉ

### Authentication
- JWT avec clés ES256
- Rotation des clés toutes les 24h
- Refresh token avec durée de vie de 30 jours

### Rate Limiting
```typescript
interface RateLimits {
  public_endpoints: {
    points: 100,
    duration: 3600  // 1 heure
  };
  authenticated_endpoints: {
    points: 1000,
    duration: 3600
  };
  websocket_connections: {
    max_concurrent: 10,
    messages_per_minute: 600
  };
}
```

## 📊 MONITORING & PERFORMANCE

### Métriques à Collecter
```typescript
interface ServiceMetrics {
  // Performance
  response_times: {
    endpoint: string;
    p50: number;
    p95: number;
    p99: number;
  }[];
  
  // Utilisation
  requests_per_second: number;
  websocket_connections: number;
  active_subscriptions: number;
  
  // Business
  yield_strategies_active: number;
  marketplace_volume: number;
  total_liquidity_managed: number;
  
  // Infrastructure
  cpu_usage: number;
  memory_usage: number;
  db_connections: number;
  cache_hit_rate: number;
}
```

### Alerting
```typescript
interface AlertConfig {
  thresholds: {
    response_time_p95: 1000,    // ms
    error_rate: 0.01,           // 1%
    cpu_usage: 0.8,             // 80%
    memory_usage: 0.8,          // 80%
    api_success_rate: 0.99      // 99%
  };
  channels: {
    slack: string;
    email: string[];
    pagerduty?: string;
  };
}
```

## 🚀 DÉPLOIEMENT

### Infrastructure Requise
- Kubernetes avec auto-scaling
- PostgreSQL avec réplication
- Redis pour le caching
- ElasticSearch pour les logs
- Prometheus + Grafana pour monitoring

### Configuration
```typescript
interface ServiceConfig {
  database: {
    max_connections: 100;
    statement_timeout: '30s';
    idle_in_transaction_timeout: '60s';
  };
  cache: {
    default_ttl: 300;          // 5 minutes
    max_memory: '2gb';
    eviction_policy: 'allkeys-lru';
  };
  api: {
    timeout: 30000;            // 30 secondes
    max_payload_size: '10mb';
    cors: {
      allowed_origins: string[];
      max_age: 86400;
    };
  };
}
```

## 📈 ROADMAP DE DÉPLOIEMENT

### Phase 1 : Infrastructure (Semaine 1-2)
- Setup Kubernetes
- Configuration base de données
- Mise en place monitoring

### Phase 2 : Core Services (Semaine 3-4)
- Implémentation authentication
- Setup cache layer
- API de base

### Phase 3 : Features (Semaine 5-8)
- Yield Finance
- Liquidity Subscriptions
- Marketplace & IA
- LINER Index

### Phase 4 : Optimisation (Semaine 9-10)
- Fine-tuning performance
- Tests de charge
- Documentation API 