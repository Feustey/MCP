import asyncio
import time
import subprocess

def run_report():
    subprocess.run([
        "python3.9", "feustey_rag_optimization.py",
        "--ollama", "--rapport",
        "--output", "data/reports/feustey_ollama_report.md"
    ])

if __name__ == "__main__":
    while True:
        print("Génération du rapport feustey...")
        run_report()
        print("Rapport généré. Prochaine génération dans 24h.")
        time.sleep(24 * 3600)  # 24h 