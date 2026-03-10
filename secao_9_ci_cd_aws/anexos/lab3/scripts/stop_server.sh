#!/bin/bash
# stop_server.sh — Para a aplicação antes de instalar nova versão (hook ApplicationStop)
# Roda na instância Green (clonada do Blue pelo CodeDeploy), onde o Flask foi iniciado
# pelo user_data via systemd com Restart=always. É obrigatório parar o serviço systemd
# primeiro; caso contrário, o pkill mata o processo mas o systemd o reinicia imediatamente,
# deixando a porta 8080 ocupada quando o start_server.sh tentar subir a V2.

# Para e desabilita o serviço systemd (impede restart automático)
systemctl stop flask-app 2>/dev/null || true
systemctl disable flask-app 2>/dev/null || true

# Mata qualquer processo Python rodando app.py que possa ter sobrado
pkill -f "python.*app\.py" || true

# Aguarda a porta ser liberada
sleep 2

# Verifica se a porta 8080 está livre
if ss -tlnp | grep -q ':8080 '; then
    echo "ERROR: porta 8080 ainda ocupada após stop" >&2
    exit 1
fi

echo "App parado e porta 8080 liberada."
