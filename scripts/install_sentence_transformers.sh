#!/bin/bash

# Script d'installation optionnelle de sentence-transformers
# Dernière mise à jour: 9 mai 2025

set -e

echo "🤖 Installation optionnelle de sentence-transformers..."

# Activation de l'environnement virtuel
source /home/feustey/venv/bin/activate

# Installation de PyTorch CPU (plus léger et compatible)
echo "📦 Installation de PyTorch CPU..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Installation de sentence-transformers
echo "📦 Installation de sentence-transformers..."
pip install sentence-transformers

# Test de l'installation
echo "🧪 Test de l'installation..."
python3 -c "
import torch
import sentence_transformers
print(f'✅ PyTorch version: {torch.__version__}')
print(f'✅ Sentence Transformers version: {sentence_transformers.__version__}')
print('✅ Installation réussie!')
"

echo ""
echo "🎉 sentence-transformers installé avec succès!"
echo ""
echo "📝 Note: Cette installation utilise PyTorch CPU pour éviter les conflits."
echo "   Pour des performances optimales, vous pouvez installer PyTorch GPU plus tard." 