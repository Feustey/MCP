# Structure du JWT et gestion multi-tenant MCP
> Dernière mise à jour : 10 mai 2025

---

## Structure du JWT

Le token JWT utilisé pour l'authentification centralisée contient les claims suivants :

- `tenant_id` : identifiant unique du tenant (Dazbox ou nœud)
- `sub` : identifiant utilisateur (optionnel)
- `exp` : date d'expiration du token (timestamp)
- `iat` : date d'émission du token (timestamp)
- (autres claims personnalisés possibles)

Exemple de payload :
```json
{
  "tenant_id": "dazbox_123456",
  "sub": "user_42",
  "exp": 1715376000,
  "iat": 1715372400
}
```

## Gestion des tenants

- Chaque requête API doit inclure un header `Authorization: Bearer <token>`.
- Le backend extrait le `tenant_id` du JWT et isole toutes les opérations (lecture/écriture) sur les données.
- Toutes les données (documents, métriques, rapports, etc.) sont associées à un `tenant_id` et filtrées en conséquence.
- Les accès à la base de données, à Qdrant, à Redis, etc. doivent toujours être filtrés par `tenant_id`.
- Les endpoints qui manipulent des nœuds Lightning doivent vérifier que le `node_id` appartient bien au `tenant_id` du token.

## Sécurité

- La clé secrète du JWT (`SECRET_KEY`) doit être définie via une variable d'environnement.
- Les tokens JWT doivent être signés avec l'algorithme HS256.
- Les données sensibles doivent être chiffrées avant stockage (voir service de chiffrement).

---

Pour toute évolution, se référer à ce document et à la spécification cloud-native MCP. 