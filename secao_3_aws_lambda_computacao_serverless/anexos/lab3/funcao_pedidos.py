"""
funcao_pedidos.py – Função Lambda A do Lab 3 (Processador de Pedidos)

Requer a layer utils-e-requests publicada na Parte 1 do lab.
Cole este código no editor do console ou faça deploy via CLI.
"""

# Importações do Layer (disponíveis em /opt/python/ automaticamente)
from utils import formatar_resposta, log_estruturado, validar_campos_obrigatorios


def lambda_handler(event, context):
    log_estruturado("info", "Processando pedido", request_id=context.aws_request_id)

    # Validar campos obrigatórios usando utilitário da layer
    valido, erro = validar_campos_obrigatorios(
        event, ["produto_id", "quantidade", "cliente_id"]
    )
    if not valido:
        log_estruturado("erro", "Validacao falhou", motivo=erro)
        return formatar_resposta(400, {}, erro)

    # Simulação de consulta de estoque (em produção: chamada a API ou banco)
    estoque_disponivel = 100

    pedido = {
        "produto_id": event["produto_id"],
        "quantidade": event["quantidade"],
        "cliente_id": event["cliente_id"],
        "estoque_disponivel": estoque_disponivel,
        "status": "aprovado" if estoque_disponivel >= event["quantidade"] else "sem_estoque",
    }

    log_estruturado("info", "Pedido processado", status=pedido["status"])
    return formatar_resposta(200, pedido, "Pedido processado com sucesso")
