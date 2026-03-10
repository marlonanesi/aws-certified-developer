#!/usr/bin/env bash
# =============================================================================
# deploy-lambdas.sh — Lab 4: Cria as 5 funções Lambda para o Step Functions
# Ambiente: macOS / Linux / WSL (Bash/Zsh)
# Pré-requisitos: AWS CLI configurado (aws configure), zip instalado,
#                 permissões IAM adequadas
# Uso: chmod +x deploy-lambdas.sh && ./deploy-lambdas.sh
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Cores
# ---------------------------------------------------------------------------
CYAN="\033[0;36m"; GREEN="\033[0;32m"; YELLOW="\033[1;33m"
MAGENTA="\033[0;35m"; RESET="\033[0m"

step()  { echo -e "\n${CYAN}>>> $1${RESET}"; }
ok()    { echo -e "    ${GREEN}[OK]${RESET} $1"; }
warn()  { echo -e "    ${YELLOW}[WARN]${RESET} $1"; }

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------
REGION="${AWS_DEFAULT_REGION:-$(aws configure get region 2>/dev/null || echo "us-east-1")}"
ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
RUNTIME="python3.12"
ROLE_NAME="lab4-lambda-basic-role"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

declare -A FUNCTION_FILES=(
    ["lab4-validate-order"]="lambda_validate_order.py"
    ["lab4-process-premium"]="lambda_process_premium.py"
    ["lab4-process-standard"]="lambda_process_standard.py"
    ["lab4-notify-customer"]="lambda_notify_customer.py"
    ["lab4-finalize-order"]="lambda_finalize_order.py"
)

declare -A FUNCTION_HANDLERS=(
    ["lab4-validate-order"]="lambda_validate_order.lambda_handler"
    ["lab4-process-premium"]="lambda_process_premium.lambda_handler"
    ["lab4-process-standard"]="lambda_process_standard.lambda_handler"
    ["lab4-notify-customer"]="lambda_notify_customer.lambda_handler"
    ["lab4-finalize-order"]="lambda_finalize_order.lambda_handler"
)

# Ordem garantida
FUNCTION_NAMES=(
    "lab4-validate-order"
    "lab4-process-premium"
    "lab4-process-standard"
    "lab4-notify-customer"
    "lab4-finalize-order"
)

declare -A ARNS=()

# ---------------------------------------------------------------------------
# 1. Garantir IAM Role básica para Lambda
# ---------------------------------------------------------------------------
step "Verificando IAM Role '$ROLE_NAME'..."

ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query "Role.Arn" --output text 2>/dev/null || true)

if [[ -z "$ROLE_ARN" || "$ROLE_ARN" == "None" ]]; then
    warn "Role nao encontrada. Criando..."

    TRUST_FILE=$(mktemp /tmp/trust-policy.XXXXXX.json)
    cat > "$TRUST_FILE" <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "lambda.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
EOF

    ROLE_ARN=$(aws iam create-role \
        --role-name "$ROLE_NAME" \
        --assume-role-policy-document "file://$TRUST_FILE" \
        --query "Role.Arn" --output text)

    aws iam attach-role-policy \
        --role-name "$ROLE_NAME" \
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" > /dev/null

    rm -f "$TRUST_FILE"
    ok "Role criada: $ROLE_ARN"
    warn "Aguardando 10s para propagação da role na AWS..."
    sleep 10
else
    ok "Role ja existe: $ROLE_ARN"
fi

# ---------------------------------------------------------------------------
# 2. Criar/atualizar cada função Lambda
# ---------------------------------------------------------------------------
for FN_NAME in "${FUNCTION_NAMES[@]}"; do
    step "Processando: $FN_NAME"

    FN_FILE="${FUNCTION_FILES[$FN_NAME]}"
    FN_HANDLER="${FUNCTION_HANDLERS[$FN_NAME]}"
    ZIP_PATH="$SCRIPT_DIR/$FN_NAME.zip"

    # Zipar apenas o arquivo .py
    (cd "$SCRIPT_DIR" && zip -q "$ZIP_PATH" "$FN_FILE")
    ok "Arquivo zipado: $FN_NAME.zip"

    # Verificar se a função já existe
    EXISTS=$(aws lambda get-function \
        --function-name "$FN_NAME" \
        --region "$REGION" \
        --query "Configuration.FunctionArn" \
        --output text 2>/dev/null || true)

    if [[ -n "$EXISTS" && "$EXISTS" != "None" ]]; then
        ARN=$(aws lambda update-function-code \
            --function-name "$FN_NAME" \
            --zip-file "fileb://$ZIP_PATH" \
            --region "$REGION" \
            --query "FunctionArn" --output text)
        ok "Código atualizado."
    else
        ARN=$(aws lambda create-function \
            --function-name "$FN_NAME" \
            --runtime "$RUNTIME" \
            --role "$ROLE_ARN" \
            --handler "$FN_HANDLER" \
            --zip-file "fileb://$ZIP_PATH" \
            --timeout 30 \
            --region "$REGION" \
            --query "FunctionArn" --output text)
        ok "Função criada."
    fi

    ARNS["$FN_NAME"]="$ARN"
    rm -f "$ZIP_PATH"
done

# ---------------------------------------------------------------------------
# 3. Exibir ARNs para uso na definição ASL
# ---------------------------------------------------------------------------
echo -e "\n${MAGENTA}============================================================${RESET}"
echo -e "${MAGENTA} ARNs das Lambdas — cole no state-machine-definition.json${RESET}"
echo -e "${MAGENTA}============================================================${RESET}"

for FN_NAME in "${FUNCTION_NAMES[@]}"; do
    echo ""
    echo -e "  ${YELLOW}$FN_NAME${RESET}"
    echo "  ${ARNS[$FN_NAME]}"
done

echo -e "\n${MAGENTA}============================================================${RESET}"
echo -e "${MAGENTA} Substitua os placeholders ARN_lab4-* no arquivo ASL acima${RESET}"
echo -e "${MAGENTA}============================================================${RESET}\n"
