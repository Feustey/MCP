# Dictionnaire de données MCP
> Synthèse des structures principales (voir src/models.py)

## NodeData
- node_id : str — identifiant du nœud
- alias : str — nom du nœud
- capacity : float — capacité totale (sats)
- channel_count : int — nombre de canaux
- last_update : datetime
- reputation_score : float
- location : dict (optionnel)
- uptime : float (optionnel, %)
- metadata : dict

## ChannelData
- channel_id : str
- capacity : float (sats)
- fee_rate : dict (base_fee, fee_rate)
- balance : dict (local, remote)
- age : int (jours)
- last_update : datetime
- status : str (optionnel)
- policies : dict (optionnel)
- metadata : dict

## NetworkMetrics
- total_capacity : float (sats)
- total_channels : int
- total_nodes : int
- average_fee_rate : float
- last_update : datetime
- active_nodes_percentage : float (optionnel)
- average_channel_age : float (optionnel)
- metadata : dict

## NodePerformance
- node_id : str
- uptime : float (%)
- transaction_count : int
- average_processing_time : float
- last_update : datetime
- metadata : dict

## SecurityMetrics
- node_id : str
- risk_score : float
- suspicious_activity : list[str]
- last_update : datetime
- metadata : dict

## ChannelRecommendation
- source_node_id : str
- target_node_id : str
- score : float
- capacity_recommendation : dict
- fee_recommendation : dict
- created_at : datetime
- metadata : dict

> Pour le détail complet, voir src/models.py. Toute nouvelle structure doit être ajoutée ici et documentée. 