#!/bin/bash
# Script d'installation des dépendances production pour MCP API
# Installe les packages manquants de manière optimale

echo "🔧 Installation des dépendances production MCP API..."
echo "================================================="

# Fonction pour installer un package si non présent
install_if_missing() {
    package=$1
    if ! pip show $package &>/dev/null; then
        echo "📦 Installation: $package"
        pip install --no-cache-dir $package
    else
        echo "✓ Déjà installé: $package"
    fi
}

# Mise à jour pip
echo "🔄 Mise à jour pip..."
pip install --upgrade pip

# 1. Core dependencies (déjà installées mais vérification)
echo -e "\n📌 Vérification Core Dependencies..."
install_if_missing "fastapi>=0.109.0"
install_if_missing "uvicorn>=0.27.0"

# 2. ML/Data Science essentials
echo -e "\n🧮 Installation ML/Data Science..."
pip install --no-cache-dir numpy>=1.24.0
pip install --no-cache-dir scikit-learn>=1.3.0
pip install --no-cache-dir scipy>=1.11.0

# 3. AI/NLP
echo -e "\n🤖 Installation AI/NLP..."
install_if_missing "openai>=1.12.0"
install_if_missing "tiktoken>=0.6.0"

# 4. Security & Auth
echo -e "\n🔐 Installation Security..."
install_if_missing "cryptography>=41.0.0"
install_if_missing "python-jose[cryptography]>=3.3.0"
install_if_missing "bcrypt>=4.0.0"

# 5. HTTP & Networking
echo -e "\n🌐 Installation HTTP/Networking..."
install_if_missing "aiohttp>=3.9.3"
install_if_missing "requests>=2.31.0"

# 6. Logging & Monitoring
echo -e "\n📊 Installation Logging..."
install_if_missing "loguru>=0.7.2"
install_if_missing "rich>=13.7.0"

# 7. System & Performance
echo -e "\n⚡ Installation System/Performance..."
install_if_missing "psutil>=5.9.8"
install_if_missing "uvloop>=0.19.0"
install_if_missing "nest_asyncio>=1.6.0"

# 8. Rate Limiting & Caching
echo -e "\n🚦 Installation Rate Limiting..."
install_if_missing "slowapi>=0.1.9"
install_if_missing "fastapi-limiter>=0.1.5"

# 9. Scheduling
echo -e "\n⏰ Installation Scheduling..."
install_if_missing "APScheduler>=3.10.4"
install_if_missing "schedule>=1.2.1"

# 10. Lightning Network
echo -e "\n⚡ Installation Lightning Network..."
install_if_missing "lnurl>=0.5.2"
install_if_missing "bolt11>=2.0.5"

# 11. Utilities
echo -e "\n🛠️ Installation Utilities..."
install_if_missing "python-dateutil>=2.8.2"
install_if_missing "pytz>=2024.1"
install_if_missing "tenacity>=8.2.3"
install_if_missing "asyncio-throttle>=1.0.2"

# 12. Optional but recommended
echo -e "\n📚 Installation Optional (Recommended)..."
install_if_missing "gunicorn>=21.2.0"

echo -e "\n✅ Installation terminée!"
echo "================================================="
echo "📋 Résumé:"
pip list | wc -l | xargs -I {} echo "Total packages installés: {}"
echo ""
echo "🚀 L'API MCP est prête pour la production!"