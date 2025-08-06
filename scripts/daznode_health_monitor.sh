#!/bin/bash

# Monitoring de santé pour daznode
# Vérifie les métriques et envoie des alertes si nécessaire

METRICS_FILE="/tmp/daznode_metrics.prom"
TELEGRAM_BOT_TOKEN="7676575630:AAEE4ds5F9XAvqU1JtAGY-_BFN0KDSAkvDQ"
TELEGRAM_CHAT_ID="5253984937"
ALERT_THRESHOLD_SUCCESS_RATE=85
ALERT_THRESHOLD_HEALTH=70

# Vérification de la fraîcheur des métriques
if [[ ! -f "$METRICS_FILE" ]]; then
    echo "Fichier de métriques manquant"
    exit 1
fi

# Vérification de l'âge du fichier (max 10 minutes)
if [[ $(find "$METRICS_FILE" -mmin +10) ]]; then
    echo "Métriques obsolètes (> 10 minutes)"
    
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEGRAM_CHAT_ID}" \
        -d text="⚠️ <b>ALERTE DAZNODE</b>

📊 Métriques obsolètes détectées
⏰ Dernière mise à jour: > 10 minutes

🔍 Vérifier le collecteur automatique" \
        -d parse_mode="HTML" > /dev/null 2>&1
    
    exit 1
fi

# Extraction des métriques critiques
success_rate=$(grep "lightning_routing_success_rate" "$METRICS_FILE" | awk '{print $2}' | head -1)
health_score=$(grep "lightning_health_score" "$METRICS_FILE" | awk '{print $2}' | head -1)
active_channels=$(grep "lightning_active_channels" "$METRICS_FILE" | awk '{print $2}' | head -1)

# Vérification des seuils
alerts=()

if [[ $(echo "$success_rate < $ALERT_THRESHOLD_SUCCESS_RATE" | bc -l 2>/dev/null || echo "0") -eq 1 ]]; then
    alerts+=("Taux de succès faible: ${success_rate}%")
fi

if [[ $(echo "$health_score < $ALERT_THRESHOLD_HEALTH" | bc -l 2>/dev/null || echo "0") -eq 1 ]]; then
    alerts+=("Score de santé dégradé: ${health_score}")
fi

if [[ $active_channels -lt 10 ]]; then
    alerts+=("Nombre de canaux actifs faible: ${active_channels}")
fi

# Envoi d'alerte si nécessaire
if [[ ${#alerts[@]} -gt 0 ]]; then
    alert_message="🚨 <b>ALERTE DAZNODE</b>

⚡ Problèmes détectés:
"
    for alert in "${alerts[@]}"; do
        alert_message+="\n• $alert"
    done
    
    alert_message+="\n\n📊 Métriques actuelles:
• Taux de succès: ${success_rate}%
• Score de santé: ${health_score}
• Canaux actifs: ${active_channels}

⏰ $(date '+%d/%m/%Y à %H:%M')"
    
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEGRAM_CHAT_ID}" \
        -d text="$alert_message" \
        -d parse_mode="HTML" > /dev/null 2>&1
    
    echo "Alertes envoyées: ${#alerts[@]}"
else
    echo "Toutes les métriques dans les normes"
fi
