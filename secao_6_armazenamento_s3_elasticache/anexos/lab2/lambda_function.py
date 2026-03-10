import json
import urllib.parse

import boto3

s3_client = boto3.client("s3")


def lambda_handler(event, context):
    print("Evento recebido:", json.dumps(event))

    for record in event["Records"]:
        event_name = record["eventName"]
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(
            record["s3"]["object"]["key"], encoding="utf-8"
        )
        size = record["s3"]["object"].get("size", 0)

        print(f"Evento : {event_name}")
        print(f"Bucket : {bucket}")
        print(f"Objeto : {key}")
        print(f"Tamanho: {size} bytes")

        extension = key.rsplit(".", 1)[-1].lower() if "." in key else "desconhecido"

        processar_objeto(bucket, key, extension, size, event_name)

    return {"statusCode": 200, "body": "Processado com sucesso"}


def processar_objeto(
    bucket: str, key: str, extension: str, size: int, event_name: str
) -> None:
    """
    Roteia o processamento com base na extensão do arquivo.

    Em um sistema real, cada bloco chamaria um serviço diferente
    (ex: Rekognition para imagens, Glue para CSVs, Textract para PDFs).
    """
    if extension in ("jpg", "jpeg", "png", "gif", "webp"):
        print(f"[IMAGEM] Gerando thumbnail para '{key}' ({size} bytes)")
        # Exemplo de integração futura:
        # rekognition.detect_labels(Image={"S3Object": {"Bucket": bucket, "Name": key}})

    elif extension in ("csv", "json"):
        print(f"[ETL] Iniciando pipeline de dados para '{key}' ({size} bytes)")
        # Exemplo de integração futura:
        # glue_client.start_job_run(JobName="pipeline-etl", Arguments={"--input_key": key})

    elif extension == "pdf":
        print(f"[PDF] Extraindo texto de '{key}' ({size} bytes)")
        # Exemplo de integração futura:
        # textract.start_document_text_detection(DocumentLocation={"S3Object": {"Bucket": bucket, "Name": key}})

    else:
        print(f"[GENÉRICO] Arquivo '{key}' (extensão: {extension}, {size} bytes) recebido sem processamento específico")
