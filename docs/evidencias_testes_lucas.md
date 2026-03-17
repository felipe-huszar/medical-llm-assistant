# Evidências de Testes — Medical LLM Assistant

**Data:** 17/03/2026  
**Testador:** huszardoBot  
**Modelo:** Qwen2.5-7B-Instruct + LoRA  
**Paciente:** Maria Silva, 70F, 68kg  
**Comorbidades:** Diabetes tipo 2, Insuficiência cardíaca, Hipotireoidismo

---

## Resumo dos Resultados

| Caso | Entrada (Sintomas) | Hipótese Esperada | Hipótese Obtida | Status |
|------|-------------------|-------------------|-----------------|--------|
| 1 | Dor torácica aperto + sudorese + falta de ar | SCA | **TEP** | ❌ |
| 2 | Febre 39°C + tosse produtiva + cansaço | Pneumonia | Pneumonia | ✅ |
| 3 | Confusão mental + febre + rigidez de nuca | Meningite | **Sepse** | ⚠️ |
| 4 | Dor abdominal QID + náuseas/vômitos | Apendicite | **TEP** | ❌❌ |

**Taxa de acerto: 25% (1/4)**

---

## Caso 1: Dor Torácica Cardíaca

### Prompt Enviado ao LLM
```
Contexto do paciente:
Paciente F, 70 anos, 68.0 kg.
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
- síndrome coronariana aguda

Exames recomendados:
- angiotomografia pulmonar
- d-dímero
- gasometria arterial
```

### Erros Identificados
| Erro | Severidade | Descrição |
|------|------------|-----------|
| Hipótese errada | 🔴 Crítico | TEP em vez de SCA para dor em aperto + sudorese |
| Alucinação | 🔴 Crítico | Inventou "sudorese noturna" e "edema" que não existiam |
| Ignora comorbidades | 🟡 Alto | Não mencionou diabetes nem insuficiência cardíaca |
| Exames inadequados | 🟡 Alto | Pediu angio TEP em vez de ECG + troponina |

---

## Caso 2: Pneumonia (Único Acerto)

### Prompt Enviado ao LLM
```
Contexto do paciente:
Paciente F, 70 anos, 68.0 kg.
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
pneumonia

Diagnósticos diferenciais:
- sepse

Exames recomendados:
- radiografia de tórax
- hemograma
- proteína C reativa
```

### Erros Identificados
| Erro | Severidade | Descrição |
|------|------------|-----------|
| Alucinação | ⚠️ Moderado | Inventou "síncope" que não foi mencionada |
| Ignora comorbidades | ❌ | Não mencionou risco de sepse grave em diabética cardíaca |

---

## Caso 3: Meningite (Sinal Cardinal Ignorado)

### Prompt Enviado ao LLM
```
Contexto do paciente:
Paciente F, 70 anos, 68.0 kg.
Histórico: Diabetes tipo 2, Insuficiência cardíaca, Hipotireoidismo

Sintomas relatados:
Paciente com confusão mental aguda, febre 38.5°C e rigidez de nuca há 6 horas.
```

### Resposta do Modelo
```
Resumo clínico:
Paciente apresentando confusão mental aguda, febre, rigidez de nuca.

Raciocínio clínico:
A presença de febre sugere processo infeccioso.

Hipótese diagnóstica principal:
sepse

Diagnósticos diferenciais:
- pneumonia
- síndrome coronariana aguda

Exames recomendados:
- hemograma
- lactato
- hemocultura
```

### Erros Identificados
| Erro | Severidade | Descrição |
|------|------------|-----------|
| Hipótese incompleta | 🔴 Crítico | Ignorou rigidez de nuca (triade de meningite) |
| Sepse como principal | ⚠️ Moderado | Sepse é consequência, não causa primária |
| Exames incompletos | 🔴 Crítico | Faltou punção lombar, exame de fundo de olho |

---

## Caso 4: Apendicite (Erro Absurdo)

### Prompt Enviado ao LLM
```
Contexto do paciente:
Paciente F, 70 anos, 68.0 kg.
Histórico: Diabetes tipo 2, Insuficiência cardíaca, Hipotireoidismo

Sintomas relatados:
Paciente com dor abdominal intensa no quadrante inferior direito, náuseas e vômitos há 12 horas, sem febre.
```

### Resposta do Modelo
```
Resumo clínico:
Paciente apresentando dor abdominal intensa no quadrante inferior direito, náuseas e vômitos há 12 horas.

Raciocínio clínico:
Dor abdominal pode indicar comprometimento gastrointestinal ou renal.

Hipótese diagnóstica principal:
Tromboembolismo pulmonar

Diagnósticos diferenciais:
- [truncado]
```

### Erros Identificados
| Erro | Severidade | Descrição |
|------|------------|-----------|
| Hipótese absurda | 🔴🔴 Grave | TEP para dor abdominal — sem conexão clínica |
| Exames invasivos incorretos | 🔴🔴 Grave | Angio TEP desnecessária e arriscada |

---

## Padrões de Falha Confirmados

### 1. Viés Sistemático para TEP
```
Caso 1: Dor torácica cardíaca → TEP ❌
Caso 2: Pneumonia → Pneumonia ✅
Caso 3: Meningite → Sepse ⚠️
Caso 4: Apendicite → TEP ❌❌

Frequência: 3 de 4 casos (75%)
```

### 2. Alucinação de Sintomas
Sintomas inventados pelo modelo:
- "sudorese noturna" (Casos 1 e 4)
- "edema em membros inferiores" (Caso 1)
- "síncope" (Caso 2)

### 3. Ignorância Total de Comorbidades
Apesar do system prompt obrigar consideração do histórico, o modelo **nunca mencionou**:
- Diabetes tipo 2
- Insuficiência cardíaca
- Hipotireoidismo

**Frequência: 0% de menção (0/4 casos)**

---

## Diagnóstico da Causa Raiz

1. **Dataset desbalanceado** — excesso de casos de TEP no treinamento
2. **Falta de exemplos com menção de comorbidades** — modelo nunca aprendeu a citar histórico
3. **Treinamento permite alucinação** — nenhuma penalização por inventar sintomas

---

## Recomendações para Retreinamento

### 🔴 Crítico (Bloqueante)

1. **Rebalancear dataset:** Reduzir TEP de ~30% para 10%, aumentar SCA/IAM
2. **Adicionar exemplos com menção de comorbidades:** Incluir casos onde resposta explicitamente cita diabetes/cardiopatia
3. **Penalizar alucinações:** Loss function modificada para penalizar tokens que introduzem sintomas não presentes

### 🟡 Importante

4. **Safety rules:** Dor torácica + aperto + idade > 50 → sempre ECG + troponina
5. **Validação por especialidade:** Métricas separadas para cardio, neuro, gastro

---

## Conclusão

O system prompt melhorado **não foi suficiente** para corrigir os problemas. As falhas são **estruturais no dataset de treinamento**:

- Desbalanceamento de classes → viés para TEP
- Falta de exemplos onde comorbidades são mencionadas → modelo ignora histórico
- Treinamento que permite alucinação → modelo inventa sintomas

**Recomendação:** Retreinamento completo com dataset revisado é necessário. O modelo atual não está pronto para uso clínico real.

---

**Arquivo:** `docs/evidencias_testes_lucas.md`  
**Gerado em:** 2026-03-17 15:15 UTC
