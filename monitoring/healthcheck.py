#!/usr/bin/env python3
"""
Health check script pour le monitoring Telegram
"""

import sys
import asyncio
import aiohttp
import os
from datetime import datetime

async def check_monitoring_health():
    """Vérifie la santé du système de monitoring"""
    try:
        # Test de l'API Telegram
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if bot_token:
            url = f"https://api.telegram.org/bot{bot_token}/getMe"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status != 200:
                        print(f"Erreur API Telegram: {response.status}")
                        return False
        
        # Test de connectivité vers l'API MCP
        mcp_url = os.getenv("MCP_API_URL", "https://api.dazno.de")
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{mcp_url}/health", timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    print(f"Erreur API MCP: {response.status}")
                    return False
        
        print(f"Health check OK - {datetime.utcnow().isoformat()}")
        return True
        
    except Exception as e:
        print(f"Health check failed: {str(e)}")
        return False

if __name__ == "__main__":
    result = asyncio.run(check_monitoring_health())
    sys.exit(0 if result else 1)