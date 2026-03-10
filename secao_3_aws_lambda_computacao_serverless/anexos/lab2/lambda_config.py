"""
lambda_config.py – Código da função Lambda do Lab 2

Cole este código no editor do console AWS e clique em Deploy.
Simula diferentes cargas de CPU para demonstrar o impacto da memória no desempenho.
"""

import json
import math
import os
import time


def lambda_handler(event, context):
    inicio = time.time()

    # Ler configurações via variáveis de ambiente
    app_env = os.environ.get("APP_ENV", "dev")
    db_host = os.environ.get("DB_HOST", "localhost")
    feature_flag = os.environ.get("FEATURE_NOVA", "false").lower() == "true"

    # Simular carga CPU proporcional ao parâmetro do evento
    workload = event.get("workload", "light")

    if workload == "heavy":
        result = sum(math.sqrt(i) for i in range(1_000_000))
        print(f"Cálculo pesado concluído: {result:.2f}")
    elif workload == "medium":
        result = sum(math.sqrt(i) for i in range(100_000))
        print(f"Cálculo médio concluído: {result:.2f}")
    else:
        result = sum(i for i in range(1_000))
        print(f"Cálculo leve concluído: {result}")

    duracao_ms = (time.time() - inicio) * 1000

    print(f"Ambiente: {app_env}")
    print(f"DB Host: {db_host}")
    print(f"Feature Nova Ativa: {feature_flag}")
    print(f"Duração interna: {duracao_ms:.2f}ms")
    print(f"Memória configurada: {context.memory_limit_in_mb}MB")
    print(f"Tempo restante: {context.get_remaining_time_in_millis()}ms")

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "env": app_env,
                "db_host": db_host,
                "feature_flag": feature_flag,
                "workload": workload,
                "duration_ms": round(duracao_ms, 2),
                "memory_mb": context.memory_limit_in_mb,
            }
        ),
    }
