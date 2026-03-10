"""
assume_role.py – Demonstração de AssumeRole via boto3

Substitua DESTINO_ID pelo Account ID da conta destino antes de executar.
"""

import boto3

ROLE_ARN = "arn:aws:iam::<DESTINO_ID>:role/CrossAccountS3Role"
SESSION_NAME = "lab1-session"
DURATION_SECONDS = 3600  # 1 hora (mínimo: 900s)


def main():
    sts_client = boto3.client("sts")

    # Identidade atual (conta origem)
    identity = sts_client.get_caller_identity()
    print(f"[Origem] Account: {identity['Account']}")
    print(f"[Origem] ARN: {identity['Arn']}\n")

    # Assumir o role na conta destino
    response = sts_client.assume_role(
        RoleArn=ROLE_ARN,
        RoleSessionName=SESSION_NAME,
        DurationSeconds=DURATION_SECONDS,
    )

    credentials = response["Credentials"]
    print(f"AccessKeyId: {credentials['AccessKeyId']}")
    print(f"Expiration:  {credentials['Expiration']}\n")

    # Criar cliente S3 com as credenciais temporárias
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )

    # Verificar identidade com as credenciais temporárias
    sts_temp = boto3.client(
        "sts",
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
    identity_temp = sts_temp.get_caller_identity()
    print(f"[Destino] Account: {identity_temp['Account']}")
    print(f"[Destino] ARN: {identity_temp['Arn']}\n")

    # Listar buckets S3 da conta destino
    buckets = s3_client.list_buckets()
    print("Buckets S3 na conta destino:")
    for bucket in buckets.get("Buckets", []):
        print(f"  - {bucket['Name']}")


if __name__ == "__main__":
    main()
