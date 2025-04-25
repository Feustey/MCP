import asyncio
from mongo_operations import MongoOperations
from datetime import datetime
import os
import aiohttp
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

async def send_telegram_notification(bot_token: str, chat_id: str, message: str):
    """Envoie une notification via Telegram"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }) as response:
            return await response.json()

async def format_recommendations_message(recommendations):
    """Formate les recommandations pour Telegram"""
    message = "🔍 <b>Rapport DazNode</b>\n\n"
    
    if not recommendations:
        return message + "❌ Aucune recommandation trouvée."
    
    # Extraire les métriques clés
    metrics = {
        "channels": "N/A",
        "capacity": "N/A",
        "success_rate": "N/A"
    }
    
    for rec in recommendations:
        if isinstance(rec.content, str) and "Nombre de canaux insuffisant" in rec.content:
            metrics["channels"] = rec.content.split("(")[1].split(")")[0]
        elif isinstance(rec.content, str) and "Capacité moyenne" in rec.content:
            metrics["capacity"] = rec.content.split("(")[0].split("moyenne")[1].strip()
        elif isinstance(rec.content, str) and "Taux de succès" in rec.content:
            metrics["success_rate"] = rec.content.split("(")[1].split(")")[0]
    
    message += f"""📊 <b>Métriques clés :</b>
- Canaux : {metrics['channels']}
- Capacité : {metrics['capacity']}
- Taux de succès : {metrics['success_rate']}

⚠️ <b>Dernières recommandations :</b>
"""
    
    # Ajouter les 3 recommandations les plus récentes
    recent_recs = sorted(recommendations, key=lambda x: x.created_at, reverse=True)[:3]
    for i, rec in enumerate(recent_recs, 1):
        content = rec.content if isinstance(rec.content, str) else str(rec.content)
        if len(content) > 200:  # Limiter la taille du message
            content = content[:197] + "..."
        message += f"\n{i}. {content}\n"
    
    message += "\n#DazNode #Lightning #Monitoring"
    return message

async def check_recommendations():
    """Vérifie les recommandations dans MongoDB"""
    mongo_ops = MongoOperations()
    node_id = "02778f4a4eb3a2344b9fd8ee72e7ec5f03f803e5f5273e2e1a2af508910cf2b12b"
    
    recommendations = await mongo_ops.get_node_recommendations(node_id)
    print(f"\nRecommandations trouvées pour le nœud {node_id}:")
    for rec in recommendations:
        print("\nRecommandation:")
        print(f"Contenu: {rec.content}")
        print(f"Date de création: {rec.created_at}")
        print(f"Score de confiance: {rec.confidence_score}")
        print("-" * 80)
    
    return recommendations

async def test_telegram_notification():
    """Teste l'envoi de notification via Telegram"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("❌ Erreur: TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID non définis dans les variables d'environnement")
        return
    
    # Récupérer les recommandations
    recommendations = await check_recommendations()
    
    # Formater le message
    message = await format_recommendations_message(recommendations)
    
    try:
        result = await send_telegram_notification(bot_token, chat_id, message)
        if result.get("ok"):
            print("✅ Test de notification Telegram réussi!")
        else:
            print(f"❌ Erreur lors de l'envoi de la notification: {result.get('description')}")
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de la notification: {str(e)}")

async def main():
    """Fonction principale qui exécute les tests"""
    print("\n🔍 Test des recommandations MongoDB...")
    await check_recommendations()
    
    print("\n📱 Test des notifications Telegram...")
    await test_telegram_notification()

if __name__ == "__main__":
    asyncio.run(main()) 