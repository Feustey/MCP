#!/usr/bin/env python3

import asyncio
import aiohttp
import time
import statistics
from typing import List, Dict
import json
from datetime import datetime

class APIPerformanceMonitor:
    def __init__(self, base_url: str = "https://api.dazno.de"):
        self.base_url = base_url
        self.endpoints = [
            "/docs",
            "/api/v1/health",
            "/api/v1/status",
            "/redoc"
        ]
        
    async def measure_endpoint(self, session: aiohttp.ClientSession, endpoint: str) -> Dict:
        """Mesure les performances d'un endpoint"""
        url = f"{self.base_url}{endpoint}"
        timings = []
        
        for _ in range(5):
            start = time.time()
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    await response.text()
                    elapsed = (time.time() - start) * 1000  # ms
                    timings.append(elapsed)
                    await asyncio.sleep(0.5)
            except Exception as e:
                print(f"Erreur sur {endpoint}: {e}")
                timings.append(30000)  # Timeout = 30s
        
        return {
            "endpoint": endpoint,
            "avg_ms": statistics.mean(timings),
            "min_ms": min(timings),
            "max_ms": max(timings),
            "median_ms": statistics.median(timings),
            "samples": len(timings)
        }
    
    async def run_monitoring(self):
        """Lance le monitoring complet"""
        async with aiohttp.ClientSession() as session:
            tasks = [self.measure_endpoint(session, ep) for ep in self.endpoints]
            results = await asyncio.gather(*tasks)
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "base_url": self.base_url,
                "results": results,
                "summary": {
                    "total_avg_ms": statistics.mean([r["avg_ms"] for r in results]),
                    "slowest_endpoint": max(results, key=lambda x: x["avg_ms"])["endpoint"],
                    "fastest_endpoint": min(results, key=lambda x: x["avg_ms"])["endpoint"]
                }
            }
            
            print(json.dumps(report, indent=2))
            
            # Alertes si trop lent
            for result in results:
                if result["avg_ms"] > 5000:
                    print(f"⚠️ ALERTE: {result['endpoint']} très lent: {result['avg_ms']:.0f}ms")
            
            return report

if __name__ == "__main__":
    monitor = APIPerformanceMonitor()
    asyncio.run(monitor.run_monitoring())
