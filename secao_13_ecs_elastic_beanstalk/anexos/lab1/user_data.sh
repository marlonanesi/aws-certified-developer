#!/bin/bash
# user_data.sh — Script de inicialização da instância EC2
# Executado automaticamente na PRIMEIRA inicialização, como root, uma única vez.
# Limite: 16 KB. Para scripts maiores, armazene no S3 e baixe aqui.

# Atualizar pacotes do sistema
yum update -y

# Instalar jq (formatador de JSON — usado nos testes de IMDS)
yum install -y jq

# Instalar o agente SSM (Amazon Linux 2023 já traz por padrão, mas garantimos)
yum install -y amazon-ssm-agent
systemctl enable amazon-ssm-agent
systemctl start amazon-ssm-agent

# Criar um arquivo de marcação para verificar que o user data rodou
echo "EC2 Lab - User Data executado em: $(date)" > /home/ec2-user/lab_info.txt
echo "Instance ID: $(curl -s -X PUT http://169.254.169.254/latest/api/token \
  -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' | \
  xargs -I{} curl -s -H 'X-aws-ec2-metadata-token: {}' \
  http://169.254.169.254/latest/meta-data/instance-id)" >> /home/ec2-user/lab_info.txt
chown ec2-user:ec2-user /home/ec2-user/lab_info.txt

# Log de conclusão
echo "User Data concluído com sucesso!" >> /var/log/cloud-init-output.log
