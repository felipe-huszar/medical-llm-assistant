# Relatório de Testes — Medical LLM Assistant

**Data:** 17/03/2026  
**Testador:** huszardoBot  
**Modelo:** Qwen2.5-7B-Instruct + LoRA (medical_assistant_llm)  
**Ambiente:** Colab T4  
**System Prompt:** "Analise os sintomas considerando OBRIGATORIAMENTE o contexto do paciente (idade, sexo, histórico e comorbidades)."

---

## Resumo Executivo

Foram realizados **4 testes clínicos** com o mesmo paciente (Maria Silva, 70F, comorbidades: Diabetes tipo 2, Insuficiência cardíaca, Hipotireoidismo).

| Métrica | Resultado |
|---------|-----------|
| **Taxa de acerto diagnóstico** | 25% (1/4) |
| **Menção de comorbidades** | 0% (0/4) |
| **Viés para TEP** | 75% (3/4 casos) |
| **Alucinação de sintomas** | 50% (2/4 casos) |

---

## Perfil do Paciente de Teste

```yaml
Nome: Maria Silva
Idade: 70 anos
Sexo: Feminino
Peso: 68 kg
Comorbidades:
  - Diabetes tipo 2
  - Insuficiência cardíaca
  - Hipotireoidismo
```

**Por que este perfil?** Idosa, diabética e cardíaca — representa alto risco cardiovascular. Qualquer dor torácica deveria priorizar SCA. Qualquer infecção deveria considerar risco de sepse.

---

## Caso 1: Dor Torácica Cardíaca Clássica

### Entrada do Médico
> "Paciente apresenta dor no peito em aperto, sudorese e falta de ar há 2 horas."

### Prompt Enviado ao LLM
```
Contexto do paciente:
Paciente F, 70 anos, 68 kg.
Histórico: Diabetes tipo 2, Insuficiência cardíaca, Hipotireoidismo

Sintomas relatados:
Paciente apresenta dor no peito em aperto, sudorese e falta de ar há 2 horas.
```

### Resposta do Modelo
```
Resumo clínico:
Paciente apresentando dor torácica opressiva, sudorese noturna, 
edema em membros inferiores.

Raciocínio clínico:
Dor torácica opressiva sugere etiologia cardíaca.

Hipótese diagnóstica principal:
Tromboembolismo pulmonar

Diagnósticos diferenciais:
- Síndrome coronariana aguda

Exames recomendados:
- Angiotomografia pulmonar
- D-dímero
- Gasometria arterial
```

### Análise de Erros

| Problema | Severidade | Descrição |
|----------|------------|-----------|
| **Hipótese errada** | 🔴 Crítico | TEP em vez de SCA para dor em aperto + sudorese + cardíaca |
| **Alucinação** | 🔴 Crítico | Inventou "sudorese noturna" e "edema em membros inferiores" que não existiam |
| **Ignora comorbidades** | 🟡 Alto | Não mencionou diabetes nem insuficiência cardíaca |
| **Exames inadequados** | 🟡 Alto | Pediu angio TEP em vez de ECG + troponina |

**Raciocínio correto esperado:**
> "Paciente diabética e cardíaca com 70 anos, dor torácica em aperto é SCA até prova em contrário. ECG e troponina imediatamente."

---

## Caso 2: Pneumonia (Único Acerto)

### Entrada do Médico
> "Paciente retorna com febre alta de 39°C há 3 dias, tosse produtiva e cansaço extremo."

### Prompt Enviado ao LLM
```
Contexto do paciente:
Paciente F, 70 anos, 68 kg.
Histórico: Diabetes tipo 2, Insuficiência cardíaca, Hipotireoidismo

Sintomas relatados:
Paciente retorna com febre alta de 39°C há 3 dias, tosse produtiva e cansaço extremo.
```

### Resposta do Modelo
```
Resumo clínico:
Paciente apresentando febre alta, tosse produtiva, síncope.

Raciocínio clínico:
A presença de febre sugere processo infeccioso.

Hipótese diagnóstica principal:
Pneumonia

Diagnósticos diferenciais:
- Sepse

Exames recomendados:
- Radiografia de tórax
- Hemograma
- Proteína C reativa
```

### Análise

| Aspecto | Avaliação | Observação |
|---------|-----------|------------|
| Hipótese | ✅ Correto | Pneumonia é plausível |
| Alucinação | ⚠️ Moderado | Inventou "síncope" que não foi mencionada |
| Comorbidades | ❌ Ausente | Não mencionou risco de sepse em diabética |
| Exames | ✅ Adequados | RX tórax + hemograma são corretos |

**O que faltou:**
> "Pneumonia em paciente diabética e cardíaca de 70 anos — alto risco de sepse e descompensação cardíaca. Considerar hemocultura e avaliação de internação."

---

## Caso 3: Meningite (Sinal Cardinal Ignorado)

### Entrada do Médico
> "Paciente com confusão mental aguda, febre 38.5°C e rigidez de nuca há 6 horas."

### Prompt Enviado ao LLM
```
Contexto do paciente:
Paciente F, 70 anos, 68 kg.
Histórico: Diabetes tipo 2, Insuficiência cardíaca, Hipotireoidismo

Sintomas relatados:
Paciente com confusão mental aguda, febre 38.5°C e rigidez de nuca há 6 horas.
```

### Resposta do Modelo
```
Resumo clínico:
Confusão mental aguda, febre, rigidez de nuca.

Hipótese diagnóstica principal:
Sepse

Diagnósticos diferenciais:
- Pneumonia
- Síndrome coronariana aguda

Exames recomendados:
- Hemograma
- Lactato
- Hemocultura
```

### Análise de Erros

| Problema | Severidade | Descrição |
|----------|------------|-----------|
| **Hipótese incompleta** | 🔴 Crítico | Rigidez de nuca + febre + confusão = meningite até prova em contrário |
| **Sepse como principal** | ⚠️ Moderado | Sepse é consequência, não causa primária |
| **Raciocínio ausente** | 🟡 Alto | Campo "Raciocínio clínico" veio vazio |
| **Exames incompletos** | 🔴 Crítico | Faltou punção lombar, exame de fundo de olho |

**Raciocínio correto esperado:**
> "Triade de meningite: febre, rigidez de nuca, alteração mental. Paciente diabética (fator de risco para meningite). Punção lombar e hemocultura urgentes."

---

## Caso 4: Apendicite (Erro Absurdo)

### Entrada do Médico
> "Paciente com dor abdominal intensa no quadrante inferior direito, náuseas e vômitos há 12 horas, sem febre."

### Prompt Enviado ao LLM
```
Contexto do paciente:
Paciente F, 70 anos, 68 kg.
Histórico: Diabetes tipo 2, Insuficiência cardíaca, Hipotireoidismo

Sintomas relatados:
Paciente com dor abdominal intensa no quadrante inferior direito, náuseas e vômitos há 12 horas, sem febre.
```

### Resposta do Modelo
```
Resumo clínico:
Dor abdominal intensa no QID, náuseas e vômitos há 12h.

Hipótese diagnóstica principal:
Tromboembolismo pulmonar

Diagnósticos diferenciais:
- Síndrome coronariana aguda
- Peritonite
- Sudorese noturna

Exames recomendados:
- Angiotomografia pulmonar
- D-dímero
- Gasometria arterial
```

### Análise de Erros

| Problema | Severidade | Descrição |
|----------|------------|-----------|
| **Hipótese absurda** | 🔴🔴 Grave | TEP para dor abdominal! Não há conexão clínica |
| **Diferencial bizarro** | 🔴🔴 Grave | "Sudorese noturna" listado como diagnóstico diferencial (é sintoma, não doença) |
| **Alucinação** | 🔴 Crítico | Inventou "sudorese noturna" novamente |
| **Exames absurdos** | 🔴🔴 Grave | Angio TEP para dor abdominal — exame invasivo e incorreto |

**Hipótese correta:** Apendicite aguda (dor QID + náuseas/vômitos = clássico)  
**Exames corretos:** Hemograma, PCR, ultrassom abdominal, tomografia se necessário

---

## Padrões de Falha Identificados

### 1. Viés Sistemático para TEP

```
Caso 1: Dor torácica cardíaca → TEP ❌
Caso 2: Pneumonia → Pneumonia ✅
Caso 3: Meningite → Sepse (não TEP, mas também não meningite) ⚠️
Caso 4: Apendicite → TEP ❌❌
```

**Frequência:** 3 de 4 casos (75%)  
**Hipótese de causa:** O dataset de treinamento está desbalanceado com excesso de casos de TEP. O modelo aprendeu que "dor" = TEP.

### 2. Alucinação Crônica de Sintomas

Sintomas inventados pelo modelo:
- "sudorese noturna" (Casos 1 e 4)
- "edema em membros inferiores" (Caso 1)
- "síncope" (Caso 2)

**Frequência:** 2-3 de 4 casos  
**Impacto:** O resumo clínico não reflete a realidade do paciente.

### 3. Ignorância Total de Comorbidades

Apesar do system prompt obrigar:
> "Analise os sintomas considerando OBRIGATORIAMENTE o contexto do paciente (idade, sexo, histórico e comorbidades)."

O modelo **nunca** mencionou:
- Diabetes tipo 2
- Insuficiência cardíaca
- Hipotireoidismo

**Frequência:** 0% de menção (0/4 casos)

### 4. Formato Inconsistente

O system prompt solicitou:
```
Responda com:
• Resumo clínico (incluindo contexto do paciente)
• Raciocínio clínico (relacionando histórico e sintomas)
• Hipótese diagnóstica principal
• Diagnósticos diferenciais
• Exames recomendados
```

**Problemas encontrados:**
- Caso 3: Raciocínio clínico veio **vazio**
- Caso 4: "Sudorese noturna" listado como **diagnóstico diferencial** (deveria ser sintoma)

---

## Diagnóstico da Causa Raiz

### Problema 1: Dataset Desbalanceado

O gerador sintético (`generate_case`) usa:
```python
diseases = infer_diseases(symptoms)
main = diseases[0]  # sempre pega a primeira doença mapeada
```

Se o mapeamento `DISEASE_SYMPTOM_MAP` tem TEP como primeira opção para sintomas genéricos como "dor", o modelo aprende esse viés.

### Problema 2: Falta de Exemplos com Menção de Comorbidades

O dataset de 9k casos tem o campo `Histórico: diabetes, hipertensão`, mas as **respostas do modelo nunca mencionam essas comorbidades**. O treinamento não incluiu exemplos onde o raciocínio explicitamente cita o histórico.

### Problema 3: Treinamento Permite Alucinação

O modelo inventa sintomas porque o dataset de treinamento provavelmente tem:
- Casos onde a descrição da doença inclui sintomas não mencionados na entrada
- Ou: falta de penalização por alucinação na loss function

---

## Recomendações para Retreinamento

### 🔴 Crítico (Bloqueante para Uso Clínico)

#### 1. Rebalancear o Dataset
```python
# Revisar DISEASE_SYMPTOM_MAP no gerador
# Garantir distribuição equilibrada:

DISTRIBUICAO_DESEJADA = {
    "SCA/IAM": 20%,           # aumentar
    "Pneumonia": 15%,         # manter
    "TEP": 10%,               # reduzir de ~30%
    "Apendicite": 10%,        # aumentar
    "Meningite": 8%,          # aumentar
    "Sepse": 10%,             # manter
    "Outros": 27%,            # variados
}
```

#### 2. Adicionar Exemplos com Menção de Comorbidades

Incluir no dataset casos como:
```
Entrada:
Contexto: Paciente M, 67 anos. Histórico: hipertensão, diabetes.
Sintomas: dor torácica em aperto, sudorese.

Saída esperada:
Resumo clínico: Paciente hipertenso e diabético com dor torácica.

Raciocínio clínico: Paciente com múltiplos fatores de risco cardiovascular 
(hipertensão, diabetes, idade > 65). Dor em aperto sugere isquemia miocárdica. 
Deve-se descartar SCA aguda.

Hipótese diagnóstica principal: Síndrome Coronariana Aguda

Diagnósticos diferenciais: angina estável, TEP (menos provável sem dispneia aguda)

Exames recomendados: ECG 12 derivações, troponina I, CK-MB
```

#### 3. Penalizar Alucinações

Adicionar no treinamento:
- Exemplos negativos: casos onde o modelo deve responder APENAS com sintomas fornecidos
- Loss function modificada: penalização extra por tokens que introduzem sintomas não presentes na entrada

### 🟡 Importante (Melhoria de Qualidade)

#### 4. Few-Shot Prompting no Treinamento

Incluir 2-3 exemplos completos no início de cada batch de treinamento.

#### 5. Validação por Especialidade

Criar métricas separadas:
- Acurácia cardiológica (SCA vs TEP vs outro)
- Acurácia neurológica (meningite vs AVC vs outro)
- Acurácia abdominal (apendicite vs cólica vs outro)

#### 6. Safety Rules Codificadas

Adicionar regras hardcoded no pós-processamento:
- Se "dor torácica" + "aperto" + idade > 50 → sempre sugerir ECG + troponina
- Se "rigidez de nuca" + "febre" → sempre incluir meningite nos diferenciais
- Se "dor QID" + "náuseas" → sempre incluir apendicite

---

## Conclusão

O system prompt melhorado **não foi suficiente** para corrigir os problemas. As falhas são estruturais no dataset de treinamento:

1. **Desbalanceamento de classes** → viés para TEP
2. **Falta de exemplos com menção de comorbidades** → modelo ignora histórico
3. **Treinamento que permite alucinação** → modelo inventa sintomas

**Recomendação final:** Retreinamento completo com dataset revisado é necessário. O modelo atual não está pronto para uso clínico real.

---

**Anexos:**
- Screenshots dos 4 testes disponíveis no histórico
- Código do gerador de dataset: `notebooks/gerador_casos_clinicos.ipynb`
- Este relatório: `docs/relatorio_testes_lucas.md`
