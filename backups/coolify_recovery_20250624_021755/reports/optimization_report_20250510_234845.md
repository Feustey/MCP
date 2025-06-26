# Rapport d'optimisation des nœuds Lightning

*Généré le 10/05/2025 à 23:48:45*

## Statistiques globales

- Nombre total de nœuds analysés: **13**
- Nombre total d'actions: **8**

## Statistiques par profil

| Profil | Nombre | Score moyen | Rééquilibrages | Ajustements de frais | Urgences | ↑ Frais | ↓ Frais |
|--------|--------|------------|----------------|---------------------|----------|---------|--------|
| **saturated** | 2 | 58.36 | 1 | 2 | 1 | 0 | 2 |
| **abused** | 4 | 41.98 | 3 | 2 | 3 | 0 | 2 |
| **unstable** | 2 | 62.69 | 0 | 0 | 0 | 0 | 0 |
| **normal** | 1 | 66.99 | 0 | 0 | 0 | 0 | 0 |
| **inactive** | 1 | 53.22 | 0 | 0 | 0 | 0 | 0 |
| **star** | 1 | 84.53 | 0 | 0 | 0 | 0 | 0 |
| **aggressive_fees** | 1 | 68.00 | 0 | 0 | 0 | 0 | 0 |
| **routing_hub** | 1 | 90.63 | 0 | 0 | 0 | 0 | 0 |

## Détails des optimisations

### 1. Nœud: test_node_abused (Profil: abused)

- **Score**: 41.38
- **État**: Équilibre=0.2, Succès=0.65, Revenu=5000
- **Recommandation**: CRITIQUE: Rééquilibrer les canaux immédiatement et ajuster les frais
- **Actions**:
  - Rééquilibrage d'urgence de 2 canaux

### 2. Nœud: 02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b (Profil: abused)

- **Score**: 41.38
- **État**: Équilibre=0.2, Succès=0.65, Revenu=5000
- **Recommandation**: CRITIQUE: Rééquilibrer les canaux immédiatement et ajuster les frais
- **Actions**:
  - Rééquilibrage d'urgence de 2 canaux

### 3. Nœud: 02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b (Profil: abused)

- **Score**: 42.57
- **État**: Équilibre=0.2, Succès=0.65, Revenu=5000
- **Recommandation**: ATTENTION: Taux de succès faible malgré l'activité - Réviser la politique tarifaire
- **Actions**:
  - Frais diminués pour 3 canaux

### 4. Nœud: 02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b (Profil: abused)

- **Score**: 42.57
- **État**: Équilibre=0.2, Succès=0.65, Revenu=5000
- **Recommandation**: ATTENTION: Taux de succès faible malgré l'activité - Réviser la politique tarifaire
- **Actions**:
  - Rééquilibrage d'urgence de 2 canaux
  - Frais diminués pour 3 canaux

### 5. Nœud: test_node_inactive (Profil: inactive)

- **Score**: 53.22
- **État**: Équilibre=0.5, Succès=0.85, Revenu=500
- **Recommandation**: ATTENTION: Activité très faible - Vérifier connectivité ou frais trop élevés
- **Actions**: Aucune action nécessaire

### 6. Nœud: test_node_saturated (Profil: saturated)

- **Score**: 58.28
- **État**: Équilibre=0.9, Succès=0.85, Revenu=5000
- **Recommandation**: ATTENTION: Taux de succès faible malgré l'activité - Réviser la politique tarifaire
- **Actions**:
  - Rééquilibrage d'urgence de 2 canaux
  - Frais diminués pour 3 canaux

### 7. Nœud: 02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b (Profil: saturated)

- **Score**: 58.43
- **État**: Équilibre=0.9, Succès=0.85, Revenu=5000
- **Recommandation**: ATTENTION: Taux de succès faible malgré l'activité - Réviser la politique tarifaire
- **Actions**:
  - Frais diminués pour 3 canaux

### 8. Nœud: 02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b (Profil: unstable)

- **Score**: 60.88
- **État**: Équilibre=0.5, Succès=0.75, Revenu=5000
- **Recommandation**: NORMAL: Performance dans la moyenne - Améliorations possibles
- **Actions**: Aucune action nécessaire

### 9. Nœud: test_node_unstable (Profil: unstable)

- **Score**: 64.49
- **État**: Équilibre=0.5, Succès=0.75, Revenu=5000
- **Recommandation**: NORMAL: Performance dans la moyenne - Améliorations possibles
- **Actions**: Aucune action nécessaire

### 10. Nœud: test_node_normal (Profil: normal)

- **Score**: 66.99
- **État**: Équilibre=0.5, Succès=0.85, Revenu=5000
- **Recommandation**: NORMAL: Performance dans la moyenne - Améliorations possibles
- **Actions**: Aucune action nécessaire

### 11. Nœud: test_node_aggressive_fees (Profil: aggressive_fees)

- **Score**: 68.00
- **État**: Équilibre=0.5, Succès=0.85, Revenu=5000
- **Recommandation**: NORMAL: Performance dans la moyenne - Améliorations possibles
- **Actions**: Aucune action nécessaire

### 12. Nœud: test_node_star (Profil: star)

- **Score**: 84.53
- **État**: Équilibre=0.5, Succès=0.98, Revenu=10000
- **Recommandation**: BON: Performance satisfaisante - Optimisations mineures possibles
- **Actions**: Aucune action nécessaire

### 13. Nœud: test_node_routing_hub (Profil: routing_hub)

- **Score**: 90.63
- **État**: Équilibre=0.5, Succès=0.85, Revenu=20000
- **Recommandation**: EXCELLENT: Performance optimale - Maintenir configuration
- **Actions**: Aucune action nécessaire

## Conclusion

### Insights

- Le profil **saturated** a nécessité le plus d'actions correctives.
- Le profil **routing_hub** a obtenu le meilleur score moyen (90.63).

### Recommandations générales

- Mettre en place des alertes précoces pour les situations critiques qui nécessitent des interventions d'urgence.
