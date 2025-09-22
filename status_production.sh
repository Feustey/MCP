#!/bin/bash

echo "📊 STATUS MCP LIGHTNING"
echo "======================"

# Vérifier l'API
if pgrep -f "uvicorn main:app" > /dev/null; then
    echo "✅ API MCP: En cours d'exécution"
else
    echo "❌ API MCP: Arrêtée"
fi

# Vérifier le monitoring
if [ -f "monitoring.pid" ] && kill -0 $(cat monitoring.pid) 2>/dev/null; then
    echo "✅ Monitoring: En cours d'exécution (PID: $(cat monitoring.pid))"
else
    echo "❌ Monitoring: Arrêté"
fi

# Logs récents
echo ""
echo "📄 LOGS RÉCENTS:"
echo "----------------"
if [ -f "logs/monitoring.log" ]; then
    echo "Monitoring:"
    tail -n 3 logs/monitoring.log
fi

echo ""
echo "💾 DONNÉES MONITORING:"
echo "---------------------"
if [ -d "monitoring_data" ]; then
    ls -la monitoring_data/ | tail -n 5
fi
