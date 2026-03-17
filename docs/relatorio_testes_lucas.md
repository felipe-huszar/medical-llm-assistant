# Relatório de Testes — Medical LLM Assistant

**Data:** 17/03/2026  
**Testador:** huszardoBot  
**Modelo:** Qwen2.5-7B-Instruct + LoRA (medical_assistant_llm)  
**Ambiente:** Colab T4

---

## Resumo Executivo

Foram realizados **4 testes clínicos** com paciente real (Maria Silva, 70F, comorbidades: Diabetes tipo 2, Insuficiência cardíaca, Hipotireoidismo).

**Taxa de acerto diagnóstico:** 25% (1/4)  
**Menção de comorbidades:** 0% (0/4)  
**Viés detectado:** Forte tendência para Tromboembolismo Pulmonar (TEP) em 3/4 casos

---

## Casos Testados

### Caso 1: Dor Torácica Cardíaca
**Entrada:** "Paciente apresenta dor no peito em aperto, sudorese e falta de ar há 2 horas."

| Aspecto | Esperado | Obtido | Status |
|---------|----------|--------|--------|
| Hipótese Principal | SCA (Síndrome Coronariana Aguda) | TEP | ❌ |
| Menção de comorbidades | Diabetes + cardiopatia como fatores de risco | Nenhuma | ❌ |
| Alucinação | — | Inventou "sudorese noturna" e "edema" | ❌ |

**Prompt enviado ao LLM:**
```
Contexto do paciente:
Paciente F, 70 anos, 68 kg.
Histórico: Diabetes tipo 2, Insuficiência cardíaca, Hipotireoidismo

Sintomas relatados:
Paciente apresenta dor no peito em aperto, sudorese e falta de ar há 2 horas.
```

---

### Caso 2: Pneumonia
**Entrada:** "Paciente retorna com febre alta de 39°C há 3 dias, tosse produtiva e cansaço extremo."

| Aspecto | Esperado | Obtido | Status |
|---------|----------|--------|--------|
| Hipótese Principal | Pneumonia (com risco de sepse por diabetes) | Pneumonia | ✅ |
| Menção de comorbidades | Risco aumentado por diabetes/cardiopatia | Nenhuma | ❌ |

---

### Caso 3: Meningite
**Entrada:** "Paciente com confusão mental aguda, febre 38.5°C e rigidez de nuca há 6 horas."

| Aspecto | Esperado | Obtido | Status |
|---------|----------|--------|--------|
| Hipótese Principal | Meningite | Sepse | ⚠️ |
| Menção de rigidez de nuca | Como sinal cardinal | Ignorado | ❌ |

---

### Caso 4: Apendicite
**Entrada:** "Paciente com dor abdominal intensa no quadrante inferior direito, náuseas e vômitos há 12 horas, sem febre."

| Aspecto | Esperado | Obtido | Status |
|---------|----------|--------|--------|
| Hipótese Principal | Apendicite aguda | TEP | ❌❌ |
| Coerência clínica | Dor QID = abdominal | TEP = pulmonar | ❌ |

---

## Problemas Identificados

### 1. Viés de Treinamento para TEP
O modelo sugere **Tromboembolismo Pulmonar** em 3 dos 4 casos, mesmo quando:
- Sintomas são exclusivamente abdominais (Caso 4)
- Sintomas são neurológicos (Caso 3)
- Sintomas cardíacos clássicos (Caso 1)

**Hipótese:** O dataset de treinamento está desbalanceado com excesso de casos de TEP.

### 2. Alucinação de Sintomas
O modelo inventa sintomas que não foram relatados:
- "sudorese noturna" (não mencionada)
- "edema em membros inferiores" (não mencionado)

### 3. Ignorância de Comorbidades
Apesar do system prompt atualizado:
```
"Analise os sintomas considerando OBRIGATORIAMENTE o contexto do paciente 
(idade, sexo, histórico e comorbidades)."
```

O modelo **nunca menciona** diabetes, insuficiência cardíaca ou hipotireoidismo nas respostas.

### 4. Não Segue Instruções do System Prompt
O formato solicitado:
- "Resumo clínico (incluindo contexto do paciente)" → não inclui
- "Raciocínio clínico (relacionando histórico e sintomas)" → não relaciona

---

## Recomendações para Retreinamento

### Prioridade 1: Balanceamento do Dataset
```python
# Revisar DISEASE_SYMPTOM_MAP no gerador
# Reduzir peso de TEP ou aumentar casos de:
- SCA / IAM (infarto agudo do miocárdio)
- Apendicite aguda
- Meningite
- Pneumonia complicada
```

### Prioridade 2: Exemplos com Menção de Comorbidades
Incluir no dataset casos onde a resposta **explicitamente cita** o histórico:

```
Raciocínio clínico:
Paciente diabética e cardíaca com 70 anos apresentando dor torácica. 
Considerando o histórico de insuficiência cardíaca e diabetes mellitus, 
a probabilidade de evento coronariano agudo é elevada. A dor em aperto 
com irradiação é característica de isquemia miocárdica.

Hipótese diagnóstica principal:
Síndrome Coronariana Aguda (provável IAM com supra ST)
```

### Prioridade 3: Reduzir Alucinações
Adicionar no treinamento exemplos **negativos**:
- Casos onde o modelo deve responder APENAS com os sintomas fornecidos
- Penalização na loss function por alucinação de sintomas

### Prioridade 4: Few-Shot Prompting
Incluir 2-3 exemplos completos no início de cada resposta de treinamento, mostrando:
- Entrada com comorbidades
- Saída que menciona essas comorbidades no raciocínio

---

## Métricas Sugeridas para Avaliação

1. **Acurácia diagnóstica por especialidade**
   - Cardiologia: SCA vs TEP vs outro
   - Infectologia: Pneumonia vs Sepse
   - Neurologia: Meningite vs AVC vs outro

2. **Taxa de menção de comorbidades relevantes**
   - % de respostas que citam explicitamente o histórico do paciente

3. **Taxa de alucinação**
   - % de respostas com sintomas não presentes na entrada

4. **Coerência clínica**
   - A hipótese principal é compatível com os sintomas descritos?

---

## Conclusão

O system prompt melhorado **não foi suficiente** para corrigir os problemas. As falhas são estruturais no dataset de treinamento:

- Desbalanceamento de classes (excesso de TEP)
- Falta de exemplos onde comorbidades são mencionadas
- Treinamento que permite/encoraja alucinação de sintomas

**Recomendação:** Retreinamento com dataset revisado é necessário para melhoria significativa.

---

**Anexos:**
- Screenshots dos 4 testes disponíveis
- Código do gerador de dataset revisado (se aplicável)
