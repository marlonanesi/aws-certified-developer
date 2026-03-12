"""
rotation_lambda.py – Lambda de rotação customizada para Secrets Manager

Copie para o editor da função Lambda no console AWS (function name: lab5-rotation).
Implementa os 4 steps do protocolo de rotação do Secrets Manager.

Este exemplo gera uma nova senha aleatória e simula a atualização no banco de dados.
Em produção, o step 'setSecret' deve de fato atualizar a senha no banco.

IAM Policy necessária no execution role:
{
  "Effect": "Allow",
  "Action": [
    "secretsmanager:GetSecretValue",
    "secretsmanager:PutSecretValue",
    "secretsmanager:UpdateSecretVersionStage",
    "secretsmanager:DescribeSecret"
  ],
  "Resource": "*"
}
"""

import boto3
import json
import secrets
import string
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*"
PASSWORD_LENGTH = 24


def generate_password() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(PASSWORD_LENGTH))


def lambda_handler(event, context):
    secret_id = event["SecretId"]
    token = event["ClientRequestToken"]
    step = event["Step"]

    client = boto3.client("secretsmanager")
    logger.info(f"Rotacao iniciada | secret={secret_id} | step={step}")

    if step == "createSecret":
        # Verificar se a versão AWSPENDING já existe (idempotência)
        metadata = client.describe_secret(SecretId=secret_id)
        versions = metadata.get("VersionIdsToStages", {})
        if token in versions:
            if "AWSPENDING" in versions[token]:
                logger.info("Versao AWSPENDING ja existe — pulando createSecret")
                return

        # Obter credenciais atuais e gerar nova senha
        current_value = json.loads(
            client.get_secret_value(SecretId=secret_id, VersionStage="AWSCURRENT")[
                "SecretString"
            ]
        )
        current_value["password"] = generate_password()

        # Salvar como versão AWSPENDING
        client.put_secret_value(
            SecretId=secret_id,
            ClientRequestToken=token,
            SecretString=json.dumps(current_value),
            VersionStages=["AWSPENDING"],
        )
        logger.info("Nova versao AWSPENDING criada com senha gerada")

    elif step == "setSecret":
        # Em produção: conectar ao banco com a senha AWSPENDING e atualizá-la
        # pending = json.loads(client.get_secret_value(SecretId=secret_id,
        #     VersionStage='AWSPENDING')['SecretString'])
        # db.update_password(pending['username'], pending['password'])
        logger.info("setSecret: atualizacao no banco simulada")

    elif step == "testSecret":
        # Em produção: testar conexão com a senha AWSPENDING
        # pending = json.loads(client.get_secret_value(SecretId=secret_id,
        #     VersionStage='AWSPENDING')['SecretString'])
        # db.connect(pending['host'], pending['username'], pending['password'])
        logger.info("testSecret: teste de conexao simulado")

    elif step == "finishSecret":
        # Descobrir a versão atual
        metadata = client.describe_secret(SecretId=secret_id)
        current_version = None
        for v_id, stages in metadata.get("VersionIdsToStages", {}).items():
            if "AWSCURRENT" in stages and v_id != token:
                current_version = v_id
                break

        # Promover AWSPENDING → AWSCURRENT
        client.update_secret_version_stage(
            SecretId=secret_id,
            VersionStage="AWSCURRENT",
            MoveToVersionId=token,
            RemoveFromVersionId=current_version,
        )
        logger.info(f"Rotacao concluida | nova versao AWSCURRENT: {token}")

    else:
        raise ValueError(f"Step desconhecido: {step}")
