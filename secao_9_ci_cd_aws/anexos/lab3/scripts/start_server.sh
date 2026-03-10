#!/bin/bash
# start_server.sh — Inicia a aplicação após a instalação (hook ApplicationStart)
# Usa nohup com path absoluto — systemd foi desabilitado pelo stop_server.sh.

nohup python3 /var/www/app/app.py > /var/log/app.log 2>&1 &
PID=$!
echo "App iniciado com PID: $PID"

# Aguarda o processo estabilizar
sleep 3

# Verifica se o processo ainda está rodando (exit imediato indica crash)
if ! kill -0 $PID 2>/dev/null; then
    echo "ERROR: processo encerrou logo após o start" >&2
    tail -n 20 /var/log/app.log >&2
    exit 1
fi

echo "App rodando com PID: $PID"
