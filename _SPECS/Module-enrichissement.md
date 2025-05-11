# Spécifications - Module d'enrichissement de nœuds Lightning Network

## 1. Spécifications fonctionnelles

### 1.1 Vue d'ensemble
Le module `EnrichedNode` est une solution centralisée pour agréger et unifier les métadonnées de nœuds Lightning Network provenant de sources diverses. Il permettra d'obtenir une vision holistique de chaque nœud du réseau à partir d'un simple identifiant de clé publique.

### 1.2 Cas d'utilisation principaux
- Analyse complète d'un nœud potentiel pour ouverture de canal
- Évaluation de la qualité des pairs pour les scénarios de test A/B
- Optimisation de stratégies de routage basées sur des données multi-sources
- Visualisation enrichie des nœuds pour aide à la décision

### 1.3 Sources de données à intégrer

| Source | Données | Priorité | Fréquence de mise à jour |
|--------|---------|----------|--------------------------|
| Amboss | Réputation, uptime, tags communautaires, score | Haute | Quotidienne |
| LNRouter | Centralité du nœud, métriques de routage, potentiel de connectivité | Haute | Hebdomadaire |
| LND/LNBits | Canaux actuels, politique de frais, capacité, historique de routage | Critique | Temps réel |
| Mempool.space | Congestion du réseau, estimation des frais | Moyenne | Horaire |

### 1.4 Stratégie de cache et persistance
- Mise en cache des données stables (aliases, pubkeys) - validité 30 jours
- Cache temporaire des données volatiles (frais, connectivité) - validité 1 heure
- Stockage persistant des analyses historiques pour comparaison

### 1.5 Indicateurs de performance
- Temps de réponse < 2 secondes pour un nœud complet
- Support pour requêtes par lots jusqu'à 50 nœuds
- Fonctionnement en mode dégradé si certaines sources sont indisponibles

## 2. Spécifications techniques

### 2.1 Architecture du module

```python
class EnrichedNode:
    """Représentation enrichie d'un nœud Lightning Network avec données multi-sources."""
    
    def __init__(self, pubkey: str):
        self.pubkey = pubkey
        self.alias = None
        self.last_updated = None
        # Métadonnées de base
        self.basic_info = {}
        # Données spécifiques par source
        self.amboss_data = {}
        self.lnrouter_data = {}
        self.lnd_data = {}
        self.mempool_data = {}
        # Métriques composites calculées
        self.composite_scores = {}
        
    @classmethod
    async def from_all_sources(cls, pubkey: str, include_sources=None, use_cache=True):
        """Crée un objet EnrichedNode en agrégeant les données de toutes les sources disponibles."""
        # Implémentation à suivre
        
    async def update(self, sources=None):
        """Met à jour les données du nœud depuis les sources spécifiées."""
        # Implémentation à suivre
        
    def to_dict(self):
        """Convertit l'objet en dictionnaire pour sérialisation."""
        # Implémentation à suivre
        
    def get_composite_score(self, metric_name=None):
        """Récupère un score composite calculé ou tous les scores."""
        # Implémentation à suivre
```

### 2.2 Interface des connecteurs de sources

```python
class DataSourceConnector(ABC):
    """Interface abstraite pour tous les connecteurs de sources de données."""
    
    @abstractmethod
    async def get_node_data(self, pubkey: str) -> dict:
        """Récupère les données pour un nœud depuis la source."""
        pass
        
    @abstractmethod
    async def get_bulk_node_data(self, pubkeys: List[str]) -> Dict[str, dict]:
        """Récupère les données pour plusieurs nœuds en parallèle."""
        pass
        
    @abstractmethod
    def get_source_name(self) -> str:
        """Renvoie l'identifiant unique de la source."""
        pass
```

### 2.3 Implémentation du cache

```python
class NodeDataCache:
    """Gestionnaire de cache pour les données de nœuds."""
    
    def __init__(self, cache_dir: str = None, ttl_volatile: int = 3600, ttl_stable: int = 2592000):
        # Initialisation du cache avec TTL différentiés
        
    async def get(self, source: str, pubkey: str, data_type: str = "all"):
        # Récupération depuis le cache si disponible et valide
        
    async def store(self, source: str, pubkey: str, data: dict, data_type: str = "all"):
        # Stockage dans le cache avec TTL approprié
```

### 2.4 Registre centralisé des sources

```python
class DataSourceRegistry:
    """Registre central et gestionnaire des connecteurs de sources."""
    
    def __init__(self):
        self.sources = {}
        self.init_default_sources()
        
    def register_source(self, source_connector: DataSourceConnector):
        # Enregistrement d'une source de données
        
    def get_source(self, source_name: str) -> DataSourceConnector:
        # Récupération d'un connecteur par son nom
        
    def get_all_sources(self) -> List[DataSourceConnector]:
        # Liste de tous les connecteurs disponibles
```

### 2.5 Méthodes de calcul des scores composites

```python
class CompositeScoreCalculator:
    """Calculateur de scores composites à partir de données multi-sources."""
    
    @staticmethod
    def calculate_reliability_score(node_data: dict) -> float:
        # Calcul du score de fiabilité (uptime Amboss + stabilité LNRouter)
        
    @staticmethod
    def calculate_routing_potential(node_data: dict) -> float:
        # Calcul du potentiel de routage (centralité LNRouter + capacité LND)
        
    @staticmethod
    def calculate_fee_efficiency(node_data: dict) -> float:
        # Calcul de l'efficacité des frais (politique LND + contexte Mempool)
```

### 2.6 Gestion des erreurs et fallbacks

- Implémentation de timeout adaptatifs pour chaque source
- Mécanisme de retry avec backoff exponentiel
- Circuit breaker pour les sources défaillantes
- Stratégie de dégradation progressive (données partielles plutôt qu'échec complet)

### 2.7 Utilisations typiques

```python
# Récupération simple d'un nœud enrichi
node = await EnrichedNode.from_all_sources("02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b")

# Extraction d'un score composite
routing_score = node.get_composite_score("routing_potential")

# Récupération sélective
node = await EnrichedNode.from_all_sources(
    "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b",
    include_sources=["amboss", "lnd"]
)

# Mise à jour des données spécifiques
await node.update(sources=["mempool"])
```

## 3. Plan d'implémentation

### Phase 1 : Infrastructure de base
- Création des interfaces abstraites
- Implémentation du système de cache
- Registre des sources

### Phase 2 : Connecteurs de sources
- Connecteur LND/LNBits (priorité 1)
- Connecteur Amboss (priorité 2)
- Connecteur LNRouter (priorité 3)
- Connecteur Mempool.space (priorité 4)

### Phase 3 : Algorithmes de scoring
- Calcul des scores composites
- Système de pondération configurable
- Visualisation des contributeurs aux scores

### Phase 4 : Intégration et optimisations
- Intégration au système RAG
- Optimisation des performances par batch processing
- Documentation et tests unitaires

## 4. Notes importantes

- Ce document se trouve dans le répertoire `_SPECS` qui contient uniquement des spécifications techniques.
- L'implémentation de ce module ne doit PAS inclure d'imports ou de références au répertoire `_SPECS`.
- L'implémentation finale devra être placée dans un module dédié (probablement dans `/rag` ou `/app/services`).
