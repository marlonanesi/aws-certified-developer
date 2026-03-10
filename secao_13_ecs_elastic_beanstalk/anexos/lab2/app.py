import os
from flask import Flask, jsonify

app = Flask(__name__)

# Lidas do environment — configuradas pelo .ebextensions/01_env.config
APP_VERSION = os.environ.get("APP_VERSION", "1.0")
APP_ENV     = os.environ.get("APP_ENV", "desenvolvimento")
EQUIPE      = os.environ.get("EQUIPE", "indefinida")


@app.route("/")
def index():
    """Endpoint principal — retorna mensagem de boas-vindas."""
    return jsonify({
        "mensagem": f"Elastic Beanstalk Lab — versao {APP_VERSION}",
        "ambiente": APP_ENV,
        "equipe": EQUIPE,
        "dica": "Acesse /health para o health check e /info para detalhes do servidor"
    })


@app.route("/health")
def health():
    """Health check — o Beanstalk consulta este endpoint para verificar a saude da instancia."""
    return jsonify({"status": "ok"}), 200


@app.route("/info")
def info():
    """Informacoes do servidor — demonstra variáveis de ambiente e IMDS."""
    import socket
    import platform

    # Tentar obter metadados da instância via IMDS v2
    instance_id = "N/A (nao rodando em EC2)"
    try:
        import urllib.request
        token_req = urllib.request.Request(
            "http://169.254.169.254/latest/api/token",
            method="PUT",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"}
        )
        with urllib.request.urlopen(token_req, timeout=2) as resp:
            token = resp.read().decode()

        meta_req = urllib.request.Request(
            "http://169.254.169.254/latest/meta-data/instance-id",
            headers={"X-aws-ec2-metadata-token": token}
        )
        with urllib.request.urlopen(meta_req, timeout=2) as resp:
            instance_id = resp.read().decode()
    except Exception:
        pass

    return jsonify({
        "versao_app": APP_VERSION,
        "ambiente": APP_ENV,
        "equipe": EQUIPE,
        "hostname": socket.gethostname(),
        "python": platform.python_version(),
        "instance_id_imds": instance_id,
        "variaveis_de_ambiente": {
            "APP_VERSION": APP_VERSION,
            "APP_ENV": APP_ENV,
            "EQUIPE": EQUIPE
        }
    })


if __name__ == "__main__":
    # Porta 5000 para execução local; o Beanstalk usa a porta definida no Procfile
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=(APP_ENV == "desenvolvimento"))
