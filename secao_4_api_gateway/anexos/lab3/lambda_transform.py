"""
lambda_transform.py – Código da função Lambda do Lab 3 (Custom Integration)

Cole este código no editor do console (função api-lab3-transform) e clique em Deploy.
Esta função NÃO usa Proxy Integration — ela recebe apenas o JSON que o VTL produziu.
"""

import json


def lambda_handler(event, context):
    # Com Custom Integration, o evento contém APENAS o que o Mapping Template definiu
    print("Evento pós-VTL:", json.dumps(event))

    full_name = event.get("fullName", "Desconhecido").strip()
    name_length = event.get("nameLength", 0)

    # Validação: ambos firstName e lastName precisam estar presentes
    if not full_name or full_name == " ":
        raise ValueError("firstName e lastName são obrigatórios")

    return {
        "greeting": f"Olá, {full_name}!",
        "chars": name_length,
        "processed": True,
    }
