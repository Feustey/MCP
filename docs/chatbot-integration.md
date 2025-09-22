# Chatbot Intelligence pour dazno.de - Guide d'Intégration

## Vue d'ensemble

Ce document décrit l'implémentation d'un chatbot intelligent pour le site dazno.de, capable d'analyser les nœuds Lightning Network et de fournir des réponses contextuelles personnalisées.

## Architecture du Chatbot

### 1. Endpoint Principal

```bash
POST /api/v1/chatbot/ask
```

**Payload:**
```json
{
  "message": "Comment va mon nœud Lightning ?",
  "node_pubkey": "02b1fe652cfc61f1e5cef78c08d60918d9fad3f029808f995a959e0a9dcbd33bab",
  "context": {
    "user_id": "user123",
    "session": "session456"
  },
  "conversation_id": "conv789"
}
```

**Réponse:**
```json
{
  "response": "🔍 **Analyse de votre nœud barcelona-big:**\\n\\n📊 **Performance actuelle:**\\n• Centralité estimée: 0.150 (Très bon)\\n• ROI annuel estimé: 8.5%\\n• Canaux ouverts: 42\\n• Capacité totale: 5,000,000 sats\\n\\n✅ Votre nœud semble bien positionné dans le réseau Lightning.",
  "node_analysis": {
    "alias": "barcelona-big",
    "pubkey": "02b1fe652cfc61f1e5cef78c08d60918d9fad3f029808f995a959e0a9dcbd33bab",
    "estimated_centrality": 0.15,
    "estimated_roi": 8.5,
    "channel_count": 42,
    "total_capacity": 5000000,
    "last_analyzed": "2024-03-15T10:30:00Z"
  },
  "suggestions": [
    "Consultez l'analyse complète de centralité",
    "Analysez vos frais pour optimiser les revenus",
    "Vérifiez l'équilibrage de vos canaux"
  ],
  "confidence": 0.9,
  "response_type": "node_specific"
}
```

### 2. Endpoints Auxiliaires

```bash
GET /api/v1/chatbot/node-summary/{node_pubkey}
GET /api/v1/chatbot/health
```

## Fonctionnalités Intelligentes

### 1. Détection d'Intention

Le chatbot analyse automatiquement l'intention de l'utilisateur :

- **Performance du nœud** : "Comment va mon nœud ?", "État de mon node", "Performance"
- **Optimisation des frais** : "Mes frais sont-ils bons ?", "Comment optimiser"
- **Gestion de liquidité** : "Problème de liquidité", "Équilibrage des canaux"
- **Routage** : "Peu de routage", "Améliorer le forwarding"

### 2. Réponses Contextuelles

Basées sur les métriques réelles du nœud :

```javascript
// Exemple d'analyse contextuelle
if (node.centrality > 0.15) {
  response += "Votre position de hub est excellente";
  suggestions.push("Ajustez vos frais vers le haut");
} else {
  response += "Améliorez votre centralité";
  suggestions.push("Ouvrez plus de canaux stratégiques");
}
```

### 3. Intégration avec l'Analyse MCP

Le chatbot utilise les endpoints d'analyse avancée :

- `/api/v1/lightning/nodes/{pubkey}/enhanced-analysis`
- `/api/v1/lightning/nodes/{pubkey}/centrality-metrics`
- `/api/v1/lightning/nodes/{pubkey}/financial-analysis`

## Implémentation Frontend

### 1. Interface Chatbot

```html
<div id="mcp-chatbot">
  <div id="chat-messages"></div>
  <div id="chat-input">
    <input type="text" id="message-input" placeholder="Posez votre question...">
    <input type="text" id="node-input" placeholder="Votre nœud (optionnel)">
    <button id="send-btn">Envoyer</button>
  </div>
</div>
```

### 2. JavaScript Integration

```javascript
class MCPChatbot {
  constructor(apiKey, baseUrl = 'https://api.dazno.de') {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
    this.conversationId = this.generateUUID();
  }

  async askQuestion(message, nodePubkey = null) {
    const response = await fetch(`${this.baseUrl}/api/v1/chatbot/ask`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`
      },
      body: JSON.stringify({
        message: message,
        node_pubkey: nodePubkey,
        conversation_id: this.conversationId
      })
    });

    return await response.json();
  }

  displayResponse(response) {
    const messagesDiv = document.getElementById('chat-messages');
    
    // Message principal
    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-response';
    messageDiv.innerHTML = this.formatResponse(response.response);
    messagesDiv.appendChild(messageDiv);

    // Suggestions
    if (response.suggestions) {
      const suggestionsDiv = document.createElement('div');
      suggestionsDiv.className = 'chat-suggestions';
      response.suggestions.forEach(suggestion => {
        const btn = document.createElement('button');
        btn.textContent = suggestion;
        btn.onclick = () => this.askQuestion(suggestion);
        suggestionsDiv.appendChild(btn);
      });
      messagesDiv.appendChild(suggestionsDiv);
    }
  }

  formatResponse(text) {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\\n/g, '<br>')
      .replace(/•/g, '•');
  }
}

// Utilisation
const chatbot = new MCPChatbot('your-api-key');

document.getElementById('send-btn').addEventListener('click', async () => {
  const message = document.getElementById('message-input').value;
  const nodePubkey = document.getElementById('node-input').value;
  
  const response = await chatbot.askQuestion(message, nodePubkey);
  chatbot.displayResponse(response);
});
```

## Cas d'Usage Typiques

### 1. Questions de Performance

```
User: "Comment va mon nœud Lightning ?"
Node: "02b1fe652cfc61f1e5cef78c08d60918d9fad3f029808f995a959e0a9dcbd33bab"

Bot: "🔍 Analyse de votre nœud barcelona-big:
📊 Performance actuelle:
• Centralité estimée: 0.150 (Très bon)
• ROI annuel estimé: 8.5%
• Canaux ouverts: 42
✅ Votre nœud semble bien positionné."
```

### 2. Optimisation des Frais

```
User: "Mes frais sont-ils optimaux ?"

Bot: "💰 Optimisation des frais Lightning:
• Frais de base recommandés: 1-10 sats
• Frais proportionnels: 100-1000 ppm
📈 Avec votre centralité de 0.15, vous pouvez ajuster vos frais vers le haut."
```

### 3. Problèmes de Liquidité

```
User: "J'ai des problèmes de liquidité"

Bot: "💧 Gestion de la liquidité Lightning:
• L'équilibrage des canaux est crucial
• Visez 50/50 local/remote
• Surveillez les canaux déséquilibrés
💡 Avec 42 canaux, diversifiez vos connexions."
```

## Configuration et Déploiement

### 1. Variables d'Environnement

```bash
CHATBOT_API_KEY=your-mcp-api-key
CHATBOT_BASE_URL=https://api.dazno.de
CHATBOT_DEFAULT_NODE=02b1fe652cfc61f1e5cef78c08d60918d9fad3f029808f995a959e0a9dcbd33bab
```

### 2. Intégration CSS

```css
#mcp-chatbot {
  max-width: 600px;
  margin: 20px auto;
  border: 1px solid #ddd;
  border-radius: 8px;
}

#chat-messages {
  height: 400px;
  overflow-y: auto;
  padding: 15px;
}

.chat-response {
  background: #f5f5f5;
  padding: 10px;
  margin: 10px 0;
  border-radius: 5px;
  border-left: 3px solid #007bff;
}

.chat-suggestions button {
  margin: 5px;
  padding: 8px 12px;
  border: 1px solid #007bff;
  background: white;
  color: #007bff;
  border-radius: 15px;
  cursor: pointer;
}

.chat-suggestions button:hover {
  background: #007bff;
  color: white;
}
```

## API de Test

Pour tester le système sans déploiement complet :

```bash
# Test de santé
curl -X GET "https://api.dazno.de/api/v1/chatbot/health"

# Test avec nœud spécifique
curl -X POST "https://api.dazno.de/api/v1/chatbot/ask" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer mcp_2f0d711f886ef6e2551397ba90b5152dfe6b23d4" \
  -d '{
    "message": "Comment va mon nœud Lightning ?",
    "node_pubkey": "02b1fe652cfc61f1e5cef78c08d60918d9fad3f029808f995a959e0a9dcbd33bab"
  }'

# Test sans nœud (général)
curl -X POST "https://api.dazno.de/api/v1/chatbot/ask" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer mcp_2f0d711f886ef6e2551397ba90b5152dfe6b23d4" \
  -d '{
    "message": "Comment optimiser mes frais Lightning ?"
  }'
```

## Métriques et Monitoring

Le chatbot fournit des métriques de performance :

- **Confidence Score** : Niveau de confiance dans la réponse (0-1)
- **Response Type** : Type de réponse (general, node_specific, analysis, error)
- **Intent Detection** : Intention détectée dans le message
- **Node Analysis Quality** : Qualité de l'analyse du nœud (complete, partial, error)

## Conclusion

Le chatbot MCP offre une interface conversationnelle intelligente pour l'analyse des nœuds Lightning Network, avec des réponses personnalisées basées sur les métriques réelles des nœuds. Il s'intègre parfaitement avec le système d'analyse avancée de dazno.de pour fournir des conseils précis et actionnables.