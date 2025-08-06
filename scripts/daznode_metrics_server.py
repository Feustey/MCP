#!/usr/bin/env python3

"""
Serveur HTTP simple pour exposer les métriques daznode
Compatible avec Prometheus, sans dépendances externes
"""

import http.server
import socketserver
import os
import json
from datetime import datetime

METRICS_FILE = "/tmp/daznode_metrics.prom"
SERVER_PORT = 9091

class MetricsHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            self.serve_metrics()
        elif self.path == "/health":
            self.serve_health()
        elif self.path == "/":
            self.serve_status()
        else:
            self.send_error(404)
    
    def serve_metrics(self):
        """Sert les métriques Prometheus"""
        try:
            if os.path.exists(METRICS_FILE):
                with open(METRICS_FILE, 'r') as f:
                    content = f.read()
                
                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))
            else:
                self.send_error(503, "Metrics file not found")
        except Exception as e:
            self.send_error(500, f"Error reading metrics: {e}")
    
    def serve_health(self):
        """Health check"""
        try:
            file_exists = os.path.exists(METRICS_FILE)
            file_age = 0
            
            if file_exists:
                file_age = datetime.now().timestamp() - os.path.getmtime(METRICS_FILE)
            
            status = {
                "status": "healthy" if file_exists and file_age < 600 else "degraded",
                "metrics_file_exists": file_exists,
                "metrics_age_seconds": int(file_age),
                "timestamp": datetime.now().isoformat()
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status).encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Health check error: {e}")
    
    def serve_status(self):
        """Page de statut"""
        html = """
        <!DOCTYPE html>
        <html>
        <head><title>Daznode Metrics Server</title></head>
        <body>
        <h1>⚡ Daznode Metrics Server</h1>
        <p><strong>Status:</strong> Running</p>
        <p><strong>Port:</strong> %d</p>
        <p><strong>Endpoints:</strong></p>
        <ul>
            <li><a href="/metrics">/metrics</a> - Prometheus metrics</li>
            <li><a href="/health">/health</a> - Health check</li>
        </ul>
        <p><strong>Last update:</strong> %s</p>
        </body>
        </html>
        """ % (SERVER_PORT, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Supprime les logs par défaut"""
        pass

if __name__ == "__main__":
    try:
        with socketserver.TCPServer(("", SERVER_PORT), MetricsHandler) as httpd:
            print(f"Serveur métriques daznode démarré sur port {SERVER_PORT}")
            print(f"Métriques: http://localhost:{SERVER_PORT}/metrics")
            print(f"Santé: http://localhost:{SERVER_PORT}/health")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
    except Exception as e:
        print(f"Erreur serveur: {e}")
