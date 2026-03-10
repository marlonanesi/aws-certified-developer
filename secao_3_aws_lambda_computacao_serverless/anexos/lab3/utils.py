"""
utils.py – Módulo utilitário compartilhado via Lambda Layer (Lab 3)

Este arquivo deve ser empacotado dentro da layer no caminho:
  python/lib/python3.12/site-packages/utils.py

Todas as funções Lambda que usarem a layer poderão importar diretamente:
  from utils import formatar_resposta, validar_campos_obrigatorios, log_estruturado
"""

import datetime
import json


def formatar_resposta(status_code: int, dados: dict, mensagem: str = None) -> dict:
    """Formata resposta padrão para funções Lambda."""
    corpo = {"dados": dados}
    if mensagem:
        corpo["mensagem"] = mensagem
    corpo["timestamp"] = datetime.datetime.utcnow().isoformat()

    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(corpo, default=str, ensure_ascii=False),
    }


def validar_campos_obrigatorios(dados: dict, campos: list) -> tuple:
    """
    Valida se todos os campos obrigatórios estão presentes e não são None.
    Retorna (True, None) se válido ou (False, mensagem_de_erro) se inválido.
    """
    faltando = [c for c in campos if c not in dados or dados[c] is None]
    if faltando:
        return False, f"Campos obrigatorios faltando: {', '.join(faltando)}"
    return True, None


def log_estruturado(nivel: str, mensagem: str, **kwargs) -> None:
    """
    Emite log no formato JSON estruturado para facilitar queries no CloudWatch Logs Insights.

    Exemplo de query:
        fields @timestamp, nivel, mensagem
        | filter nivel = "erro"
        | sort @timestamp desc
    """
    entrada = {
        "nivel": nivel.upper(),
        "mensagem": mensagem,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        **kwargs,
    }
    print(json.dumps(entrada, ensure_ascii=False))
