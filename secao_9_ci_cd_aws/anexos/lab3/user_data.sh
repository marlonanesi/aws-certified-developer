#!/bin/bash
# user_data.sh — Script de User Data para instâncias EC2 do Lab 3
# Instala o CodeDeploy Agent, Python/Flask e sobe a aplicação v1 (Blue) na porta 8080.
#
# Diagnóstico: sudo cat /var/log/user-data.log

# Redireciona toda saída para log — essencial para depurar falhas na segunda instância
exec > >(tee /var/log/user-data.log | logger -t user-data -s 2>/dev/console) 2>&1

set -euo pipefail

echo "[$(date -u +%FT%TZ)] === user_data iniciado ==="

echo "[$(date -u +%FT%TZ)] Atualizando pacotes..."
yum update -y

echo "[$(date -u +%FT%TZ)] Instalando dependências..."
yum install -y ruby wget python3

echo "[$(date -u +%FT%TZ)] Instalando pip e Flask..."
python3 -m ensurepip --upgrade 2>/dev/null || true
python3 -m pip install --upgrade pip -q
python3 -m pip install flask -q

# Obtém a região via IMDSv2 obrigatório — IMDSv1 desabilitado por padrão nas AMIs atuais
echo "[$(date -u +%FT%TZ)] Obtendo região via IMDSv2..."
IMDS="http://169.254.169.254"
TOKEN=""
REGION=""

# Passo 1: obter o token IMDSv2 (falha rápida e explícita se não conseguir)
for i in $(seq 1 15); do
    TOKEN=$(curl -s -X PUT "${IMDS}/latest/api/token" \
        -H "X-aws-ec2-metadata-token-ttl-seconds: 60" --max-time 3) || true
    [ -n "$TOKEN" ] && break
    echo "[$(date -u +%FT%TZ)] IMDSv2 token não disponível ainda (tentativa $i/15)..."
    sleep 3
done

if [ -z "$TOKEN" ]; then
    echo "[$(date -u +%FT%TZ)] ERROR: IMDSv2 não respondeu após 15 tentativas." \
         "Verifique se HttpTokens=required está ativo e hop limit >= 1." >&2
    exit 1
fi
echo "[$(date -u +%FT%TZ)] Token IMDSv2 obtido."

# Passo 2: buscar a região usando o token (sem fallback IMDSv1)
REGION=$(curl -s --max-time 5 \
    -H "X-aws-ec2-metadata-token: $TOKEN" \
    "${IMDS}/latest/meta-data/placement/region")

if [ -z "$REGION" ]; then
    echo "[$(date -u +%FT%TZ)] ERROR: token IMDSv2 válido mas /placement/region retornou vazio." >&2
    exit 1
fi
echo "[$(date -u +%FT%TZ)] Região: $REGION"

echo "[$(date -u +%FT%TZ)] Instalando CodeDeploy Agent..."
cd /tmp
wget -q "https://aws-codedeploy-${REGION}.s3.${REGION}.amazonaws.com/latest/install"
chmod +x ./install
./install auto
systemctl enable codedeploy-agent
systemctl start codedeploy-agent

echo "[$(date -u +%FT%TZ)] Verificando CodeDeploy Agent..."
for i in $(seq 1 10); do
    systemctl is-active --quiet codedeploy-agent && break
    echo "[$(date -u +%FT%TZ)] Aguardando codedeploy-agent iniciar (tentativa $i)..."
    sleep 3
done
systemctl is-active --quiet codedeploy-agent || {
    echo "[$(date -u +%FT%TZ)] ERROR: codedeploy-agent não iniciou" >&2
    journalctl -u codedeploy-agent --no-pager -n 20 >&2
    exit 1
}

echo "[$(date -u +%FT%TZ)] Criando aplicação v1 (Blue)..."
mkdir -p /var/www/app/scripts

cat > /var/www/app/app.py << 'EOF'
from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return 'V1 - Blue Environment'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
EOF

# Serviço systemd — garante que o Flask suba sempre,
# inclusive em instâncias Green clonadas pelo CodeDeploy
cat > /etc/systemd/system/flask-app.service << 'EOF'
[Unit]
Description=Flask App
After=network.target

[Service]
ExecStart=/usr/bin/python3 /var/www/app/app.py
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable flask-app
systemctl start flask-app

echo "[$(date -u +%FT%TZ)] Verificando Flask..."
for i in $(seq 1 10); do
    curl -sf http://localhost:8080 > /dev/null && break
    echo "[$(date -u +%FT%TZ)] Aguardando Flask na porta 8080 (tentativa $i)..."
    sleep 3
done
curl -sf http://localhost:8080 > /dev/null || {
    echo "[$(date -u +%FT%TZ)] ERROR: Flask não respondeu na porta 8080" >&2
    journalctl -u flask-app --no-pager -n 20 >&2
    exit 1
}

echo "[$(date -u +%FT%TZ)] === user_data concluído com sucesso ==="
# Marcador de conclusão — verificável via: test -f /var/log/user-data-done
touch /var/log/user-data-done
