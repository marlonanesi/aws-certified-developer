# LAB 117 — CloudWatch Métricas e Dashboards na Prática
> **USO INTERNO — Guia do Instrutor**

## Objetivo
Demonstrar na prática: visualizar métricas nativas, criar um dashboard customizado, habilitar Detailed Monitoring no EC2 e publicar uma métrica customizada via CLI.

---

## Pré-requisitos
- Conta AWS com permissões: CloudWatch Full, EC2 (describe), Lambda (invoke)
- AWS CLI configurada
- Uma função Lambda já existente (ou criar uma simples para o lab)

---

## Roteiro do Lab

### Parte 1 — Explorando Métricas Nativas (5 min)
1. Console AWS → CloudWatch → **Metrics → All metrics**
2. Abrir namespace `AWS/Lambda`
3. Selecionar dimensão `FunctionName` → escolher sua função
4. Adicionar ao gráfico: `Invocations`, `Errors`, `Duration`
5. Alterar o período para **1 minuto** e a estatística de Duration para **p99**
6. **Pontos de ensino:** namespace, dimensão, período, estatística

### Parte 2 — Criar Dashboard (5 min)
1. CloudWatch → **Dashboards → Create dashboard** → nome: `Lab-Dev-Dashboard`
2. Add widget → **Line** → selecionar `AWS/Lambda/Duration`
3. Add widget → **Number (Gauge)** → selecionar `AWS/Lambda/Errors`
4. Add widget → **Alarm status** (criar um alarme rápido de Errors > 0 primeiro se não houver)
5. Salvar dashboard
6. Mostrar que pode adicionar widgets de regiões diferentes

### Parte 3 — Detailed Monitoring EC2 (3 min)
> Se não tiver EC2, pode demonstrar via console sem instância ativa
1. EC2 → selecionar uma instância → **Monitoring** → Enable Detailed Monitoring
2. Mostrar a diferença: **5 minutos** (Basic) vs **1 minuto** (Detailed)
3. Ressaltar custo adicional (USD 3,50/instância/mês)

### Parte 4 — Publicar Métrica Customizada via CLI (5 min)
```bash
# Publicar métrica customizada
aws cloudwatch put-metric-data \
  --namespace "MeuCurso/Lab" \
  --metric-name "PedidosSimulados" \
  --value 42 \
  --unit Count \
  --dimensions "Ambiente=Dev"

# Verificar se apareceu
aws cloudwatch list-metrics \
  --namespace "MeuCurso/Lab"

# Publicar mais alguns valores para gerar histórico
for i in 10 25 50 15 38; do
  aws cloudwatch put-metric-data \
    --namespace "MeuCurso/Lab" \
    --metric-name "PedidosSimulados" \
    --value $i \
    --unit Count \
    --dimensions "Ambiente=Dev"
  sleep 1
done
```
5. No console: Metrics → Custom namespaces → MeuCurso/Lab → visualizar no gráfico

### Parte 5 — Alarme Rápido (3 min)
1. CloudWatch → Alarms → Create alarm
2. Selecionar `PedidosSimulados` do namespace `MeuCurso/Lab`
3. Threshold: >= 45, período 1 min, 1 evaluation period
4. Ação: criar tópico SNS com seu e-mail
5. Publicar valor 50 via CLI e mostrar o alarme entrar em ALARM
6. Publicar valor 5 e mostrar retorno para OK

---

## Cleanup
```bash
# Deletar dashboard
aws cloudwatch delete-dashboards --dashboard-names Lab-Dev-Dashboard

# Deletar alarme (pegar o nome do alarme criado)
aws cloudwatch delete-alarms --alarm-names NomeDoAlarme
```

## Pontos de Atenção para Gravação
- Tempo total estimado: 20-25 minutos de gravação
- Sempre mostrar o JSON da chamada CLI com formatação visível
- Ressaltar o delay de ~1 minuto para métricas aparecerem no console
- Após criar alarme com e-mail SNS, confirmar a subscription no e-mail antes de gravar
