"""
lambda_backend.py – Código da função Lambda do Lab 3

Copie este código para o editor da função Lambda no console AWS.
A função extrai claims do token JWT via requestContext (Lambda Proxy Integration).
"""


def lambda_handler(event, context):
    # Com Cognito Authorizer + Lambda Proxy Integration, os claims ficam em:
    # event["requestContext"]["authorizer"]["claims"]
    request_context = event.get("requestContext", {})
    authorizer = request_context.get("authorizer", {})
    claims = authorizer.get("claims", {})

    email = claims.get("email", "N/A")
    sub = claims.get("sub", "N/A")
    groups = claims.get("cognito:groups", "N/A")

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": (
            f'{{"message": "Acesso autorizado", '
            f'"email": "{email}", '
            f'"sub": "{sub}", '
            f'"groups": "{groups}"}}'
        ),
    }
