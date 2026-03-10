from http.server import HTTPServer, BaseHTTPRequestHandler


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Hello from ECR! Container rodando na AWS!")

    def log_message(self, format, *args):
        # Silencia os logs de acesso padrão do HTTPServer
        # para facilitar a leitura do output durante a demonstração.
        pass


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8080), Handler)
    print("Server running on port 8080")
    server.serve_forever()
