#!/bin/bash
# validate.sh — Verifica se a aplicação respondeu corretamente (hook ValidateService)
# O CodeDeploy considera o deploy bem-sucedido apenas se este script retornar exit 0.

for i in 1 2 3; do
    if curl -sf http://localhost:8080; then
        echo "Health check passed!"
        exit 0
    fi
    echo "Tentativa $i falhou, aguardando..."
    sleep 2
done

echo "ERROR: health check falhou após 3 tentativas" >&2
exit 1
