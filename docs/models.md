# Documentation des Modèles

## Vue d'ensemble

Le module `Models` définit les structures de données utilisées dans le système. Il utilise Pydantic pour la validation des données et la sérialisation.

## Modèles principaux

### NodeData

```python
class NodeData(BaseModel):
    pubkey: str
    alias: str
    capacity: int
    channels: int
    first_seen: datetime
    last_updated: datetime
    metadata: Optional[Dict[str, Any]] = None
```

Représente un nœud Lightning avec ses attributs principaux.

### ChannelData

```python
class ChannelData(BaseModel):
    channel_id: str
    node1_pubkey: str
    node2_pubkey: str
    capacity: int
    fee_rate: FeeRate
    last_updated: datetime
    status: ChannelStatus
```

Représente un canal Lightning avec ses caractéristiques.

### FeeRate

```python
class FeeRate(BaseModel):
    base_fee: int
    fee_rate: int
    min_htlc: int
    max_htlc: int
```

Définit la structure des frais pour un canal.

### NetworkMetrics

```python
class NetworkMetrics(BaseModel):
    total_capacity: int
    total_channels: int
    avg_channel_capacity: float
    median_channel_capacity: float
    last_update: datetime
```

Contient les métriques globales du réseau.

### RAGDocument

```python
class RAGDocument(BaseModel):
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None
    timestamp: datetime
```

Structure pour les documents du système RAG.

## Validation des données

### Règles de validation

1. **NodeData**
   - `pubkey` doit être une chaîne hexadécimale de 66 caractères
   - `capacity` doit être positif
   - `channels` doit être positif ou nul
   - `last_updated` doit être postérieur à `first_seen`

2. **ChannelData**
   - `channel_id` doit être unique
   - `capacity` doit être positif
   - `fee_rate` doit être valide
   - `status` doit être une valeur énumérée valide

3. **FeeRate**
   - `base_fee` doit être positif
   - `fee_rate` doit être positif
   - `min_htlc` doit être inférieur à `max_htlc`

## Sérialisation

### Méthodes de sérialisation

```python
def to_dict(self) -> Dict[str, Any]
```
Convertit le modèle en dictionnaire.

```python
def to_json(self) -> str
```
Convertit le modèle en JSON.

### Configuration

```python
class Config:
    json_encoders = {
        datetime: lambda dt: dt.isoformat()
    }
    allow_population_by_field_name = True
```

## Exemples d'utilisation

### Création d'un nœud

```python
node = NodeData(
    pubkey="02eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619",
    alias="MonNœud",
    capacity=1000000,
    channels=10,
    first_seen=datetime.now(),
    last_updated=datetime.now()
)
```

### Validation d'un canal

```python
channel = ChannelData(
    channel_id="1234567890",
    node1_pubkey="02eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619",
    node2_pubkey="03eec7245d6b7d2ccb30380bfbe2a3648cd7a942653f5aa340edcea1f283686619",
    capacity=500000,
    fee_rate=FeeRate(
        base_fee=1000,
        fee_rate=1,
        min_htlc=1000,
        max_htlc=1000000
    ),
    last_updated=datetime.now(),
    status=ChannelStatus.ACTIVE
)
```

## Bonnes pratiques

1. **Validation**
   - Toujours utiliser les modèles pour la validation
   - Ajouter des validateurs personnalisés si nécessaire
   - Gérer les erreurs de validation de manière appropriée

2. **Sérialisation**
   - Utiliser les méthodes de sérialisation intégrées
   - Gérer correctement les types spéciaux (datetime, etc.)
   - Documenter les formats de sortie

3. **Performance**
   - Éviter la validation excessive
   - Utiliser des types appropriés
   - Optimiser les structures de données 