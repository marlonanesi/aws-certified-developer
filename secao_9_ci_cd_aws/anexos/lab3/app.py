#!/usr/bin/env python3
"""
Aplicação de demonstração — versão 2 (Green)
Usada no Lab 3 (CodeDeploy Blue/Green) para demonstrar a nova versão
que substitui a versão 1 (Blue) durante o deploy.
"""
import http.server
import socketserver

PORT = 8080


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"V2 - Green Environment - New Version!")

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving on port {PORT}")
        httpd.serve_forever()
