"""
funcao_clientes.py – Função Lambda B do Lab 3 (Validador de Clientes)

Requer a layer utils-e-requests publicada na Parte 1 do lab.
Cole este código no editor do console ou faça deploy via CLI.
"""

# Importações do Layer (disponíveis em /opt/python/ automaticamente)
from utils import formatar_resposta, log_estruturado, validar_campos_obrigatorios


def lambda_handler(event, context):
    log_estruturado("info", "Validando cliente", request_id=context.aws_request_id)

    valido, erro = validar_campos_obrigatorios(event, ["email", "nome"])
    if not valido:
        log_estruturado("erro", "Validacao falhou", motivo=erro)
        return formatar_resposta(400, {}, erro)

    # Simulação de validação de cliente
    cliente = {
        "email": event["email"],
        "nome": event["nome"],
        "status": "ativo",
        "perfil": "basico",
    }

    log_estruturado("info", "Cliente validado", email=event["email"])
    return formatar_resposta(200, cliente, "Cliente valido")
