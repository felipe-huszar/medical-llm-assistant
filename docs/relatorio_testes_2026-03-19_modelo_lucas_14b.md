# Relatório de Testes — Medical LLM Assistant (Lucas 14B)

**Data:** 19/03/2026  
**Testador:** huszardoBot  
**Interface:** https://a766ba11c32ec96d7b.gradio.live/  
**Modelo:** Qwen2.5-14B-Instruct-bnb-4bit + LoRA (adapter do Lucas)  
**Método:** chamadas diretas à API do Gradio (`/gradio_api/call/*`) para evitar instabilidade do navegador e garantir reprodutibilidade.  
**Confirmação do modelo:** loader do Colab registrou `Carregando base model: unsloth/Qwen2.5-14B-Instruct-bnb-4bit` e depois `Aplicando LoRA adapter: /content/model`.

---

## Perfil do Paciente Benchmark

```yaml
Nome: Maria Silva Benchmark API 2
Idade: 70 anos
Sexo: Feminino
Peso: 68 kg
Comorbidades:
  - Diabetes tipo 2
  - Insuficiência cardíaca
  - Hipotireoidismo
```

## Resumo Executivo

| Métrica | Resultado |
|---------|-----------|
| **Taxa de acerto diagnóstico** | 4/4 (100%) |
| **Menção das 3 comorbidades** | 4/4 (100%) |
| **Alucinação clássica registrada** | 0/4 casos |

## Comparação rápida com baseline antigo (7B)

| Métrica | Baseline antigo | Lucas 14B |
|---------|------------------|-----------|
| Acurácia | 25% (1/4) | 100% (4/4) |
| Menção de comorbidades | 0% (0/4) | 100% (4/4) |
| Alucinação clássica | 50% (2/4) | 0% (0/4) |

---

## Caso 1: Dor Torácica Cardíaca Clássica

### Entrada
> Paciente apresenta dor no peito em aperto, sudorese e falta de ar há 2 horas.

**Hipótese esperada:** `síndrome coronariana aguda`  
**Hipótese obtida:** `síndrome coronariana aguda`  
**Status:** ✅ Correto

**Menção completa às comorbidades:** ✅ Sim

### Resposta do Modelo
```markdown
## 🩺 Análise Clínica

### 📋 Resumo Clínico
Paciente apresentando dor no peito em aperto, sudorese e falta de ar há 2 horas. Histórico relevante: diabetes tipo 2, insuficiência cardíaca, hipotireoidismo.

### 🎯 Hipótese Diagnóstica Principal
síndrome coronariana aguda

### 🔍 Diagnósticos Diferenciais
  • insuficiência cardíaca descompensada
  • tromboembolismo pulmonar
  • pneumonia

### 🧪 Exames Recomendados
  • ECG
  • troponina
  • ecocardiograma

### 💭 Raciocínio Clínico
Paciente com histórico de diabetes tipo 2, insuficiência cardíaca, hipotireoidismo, o que representa fator de risco relevante para a apresentação atual. Dor torácica opressiva em paciente com múltiplos fatores de risco cardiovasculares sugere síndrome coronariana aguda como hipótese prioritária.

---
> ⚕️ *Esta análise é apenas orientativa. A decisão clínica final é responsabilidade do médico assistente.*
```

---

## Caso 2: Pneumonia

### Entrada
> Paciente retorna com febre alta de 39°C há 3 dias, tosse produtiva e cansaço extremo.

**Hipótese esperada:** `pneumonia`  
**Hipótese obtida:** `pneumonia`  
**Status:** ✅ Correto

**Menção completa às comorbidades:** ✅ Sim

### Resposta do Modelo
```markdown
## 🩺 Análise Clínica

### 📋 Resumo Clínico
Paciente apresentando febre alta de 39°C há 3 dias, tosse produtiva e cansaço extremo. Histórico relevante: diabetes tipo 2, insuficiência cardíaca, hipotireoidismo.

### 🎯 Hipótese Diagnóstica Principal
pneumonia

### 🔍 Diagnósticos Diferenciais
  • sepse
  • insuficiência cardíaca descompensada
  • síndrome coronariana aguda

### 🧪 Exames Recomendados
  • radiografia de tórax
  • hemograma
  • proteína C reativa

### 💭 Raciocínio Clínico
Paciente com histórico de diabetes tipo 2, insuficiência cardíaca, hipotireoidismo, o que representa fator de risco relevante para a apresentação atual. Considerando o estado imunossupressor, processo infeccioso deve ser investigado com prioridade.

---
> ⚕️ *Esta análise é apenas orientativa. A decisão clínica final é responsabilidade do médico assistente.*
```

---

## Caso 3: Meningite

### Entrada
> Paciente com confusão mental aguda, febre 38.5°C e rigidez de nuca há 6 horas.

**Hipótese esperada:** `meningite bacteriana`  
**Hipótese obtida:** `meningite bacteriana`  
**Status:** ✅ Correto

**Menção completa às comorbidades:** ✅ Sim

### Resposta do Modelo
```markdown
## 🩺 Análise Clínica

### 📋 Resumo Clínico
Paciente apresentando confusão mental aguda, febre alta (38.5°C) e rigidez de nuca. Histórico relevante: diabetes tipo 2, insuficiência cardíaca, hipotireoidismo.

### 🎯 Hipótese Diagnóstica Principal
meningite bacteriana

### 🔍 Diagnósticos Diferenciais
  • sepse
  • pneumonia
  • acidente vascular cerebral

### 🧪 Exames Recomendados
  • punção lombar
  • hemograma
  • hemocultura

### 💭 Raciocínio Clínico
Paciente com histórico de diabetes tipo 2, insuficiência cardíaca, hipotireoidismo, o que representa fator de risco relevante para a apresentação atual. Considerando o estado imunossupressor, processo infeccioso deve ser investigado com prioridade. Rigidez de nuca associada a febre e alteração do nível de consciência compõem triade de meningite.

---
> ⚕️ *Esta análise é apenas orientativa. A decisão clínica final é responsabilidade do médico assistente.*
```

---

## Caso 4: Apendicite

### Entrada
> Paciente com dor abdominal intensa no quadrante inferior direito, náuseas e vômitos há 12 horas, sem febre.

**Hipótese esperada:** `apendicite aguda`  
**Hipótese obtida:** `apendicite aguda`  
**Status:** ✅ Correto

**Menção completa às comorbidades:** ✅ Sim

### Resposta do Modelo
```markdown
## 🩺 Análise Clínica

### 📋 Resumo Clínico
Paciente apresentando dor abdominal intensa no quadrante inferior direito, náuseas e vômitos há 12 horas, sem febre. Histórico relevante: diabetes tipo 2, insuficiência cardíaca, hipotireoidismo.

### 🎯 Hipótese Diagnóstica Principal
apendicite aguda

### 🔍 Diagnósticos Diferenciais
  • gastroenterite aguda
  • cólica renal
  • hemorragia subaracnoide

### 🧪 Exames Recomendados
  • hemograma
  • proteína C reativa
  • ultrassom abdominal

### 💭 Raciocínio Clínico
Paciente com histórico de diabetes tipo 2, insuficiência cardíaca, hipotireoidismo, o que representa fator de risco relevante para a apresentação atual. Dor abdominal com náuseas/vômitos requer investigação cirúrgica para excluir abdome agudo.

---
> ⚕️ *Esta análise é apenas orientativa. A decisão clínica final é responsabilidade do médico assistente.*
```

---

## Avaliação Final

- **Melhorou em relação ao baseline antigo**, especialmente em fidelidade ao contexto e menção de comorbidades.
- O 14B parece **mais obediente ao input** do que o 7B em vários cenários, mas ainda precisa de validação mais ampla.
- O ganho mais claro é em **menção de histórico/comorbidades**; o ponto ainda crítico continua sendo **calibração clínica e diferenciais**.
- Recomendação: usar este relatório como nova linha de comparação datada e manter relatórios futuros sempre com data no nome do arquivo.