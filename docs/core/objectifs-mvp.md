# Objectifs fonctionnels MVP MCP
> Extraits et adaptés de [_SPECS/Plan-MVP.md](mdc:_SPECS/Plan-MVP.md)

## Cas d'usage principaux

1. **Détection et ajustement automatique des fees**
   - Si un canal est sous-performant depuis 48h (score < seuil), augmenter la fee base de +20%.
   - Critère de succès : l'ajustement est loggé, traçable, et réversible.

2. **Rééquilibrage dynamique de la liquidité**
   - Si la liquidité sortante > 80% sur un canal, augmenter la base fee de 30% pour décourager l'épuisement.
   - Si la liquidité entrante > 80%, baisser la fee pour encourager l'utilisation.
   - Critère de succès : le système ajuste automatiquement et loggue chaque action.

3. **Shadow mode & monitoring**
   - Pendant 7 jours, le système ne fait que logguer les actions qu'il aurait prises (aucune action réelle).
   - Critère de succès : comparaison manuelle des logs avec les décisions humaines, logs complets et exploitables.

> Pour la logique détaillée, voir [_SPECS/Plan-MVP.md](mdc:_SPECS/Plan-MVP.md) et [docs/backbone-technique-MVP.md](mdc:docs/backbone-technique-MVP.md). 