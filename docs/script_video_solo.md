# Script do Vídeo — Solo (Felipe)
## Tech Challenge Fase 3 — 15 minutos

**Gravador:** Felipe Huszar (solo)  
**Formato:** screenshare + narração  
**Objetivo:** cobrir todos os critérios do enunciado numa gravação fluida

---

## Preparação (antes de apertar REC)

- [ ] Colab aberto: `colabs/system_gradio.ipynb` → Run all → aguardar URL gradio.live
- [ ] Colab do Lucas aberto (fine-tuning) — não precisa rodar, só estar visível
- [ ] 3 pacientes cadastrados no Gradio: Maria, João, Ana
- [ ] Terminal aberto com: `tail -f audit_log.jsonl` (no Colab, não local)
- [ ] GitHub repo aberto numa tab: https://github.com/felipe-huszar/medical-llm-assistant
- [ ] Diagrama renderizado: abrir `docs/diagrama_pipeline.md` no GitHub
- [ ] Testar 1 consulta rápida antes de gravar

---

## BLOCO 1 — Apresentação e problema (1:30 min)
> *Tela: GitHub repo ou slide simples*

**Fala:**

"Olá. Esse é o Tech Challenge Fase 3 — um assistente médico virtual com LLM fine-tuned e LangGraph.

O desafio era: treinar um modelo com dados médicos controlados, construir um pipeline seguro em cima dele, e garantir que o sistema nunca faça nada perigoso — como prescrever medicamento diretamente.

Eu e meu parceiro Lucas trabalhamos em duas frentes: eu fui responsável pela arquitetura do sistema, pipeline e segurança; o Lucas pelo processo de fine-tuning e treinamento dos modelos.

Vou mostrar tudo isso em 15 minutos."

---

## BLOCO 2 — Fine-tuning: a jornada (3 min)
> *Tela: Colab de fine-tuning do Lucas — aberto, não rodando*

**Fala:**

"Vou começar pelo mais difícil: o treinamento do modelo.

*(aponta para o colab)*

A parte que mais consumiu tempo não foi o código — foi o dado.

Tentamos datasets públicos em inglês, como PubMedQA e MedQuAD. Não funcionou — idioma errado, contexto clínico diferente do brasileiro.

Criamos então um **gerador de casos sintéticos próprio** — está aqui nesse colab. Geramos 5.000 casos clínicos. O modelo treinado com esses dados era limitado — faltava base médica ampla.

Misturamos com o **MedPT**, um dataset médico em português. Primeiro modelo: Mistral 7B. Ainda insatisfatório — o modelo retornava texto em prosa, não o formato estruturado que precisávamos.

A virada foi o **treinamento em duas fases**: primeiro o MedPT, para dar conhecimento médico base. Depois os casos sintéticos, para moldar o formato de resposta. Trocamos para **Qwen 2.5 7B**.

Melhorou — mas ainda havia um viés grave. Testamos 4 casos clínicos e o modelo retornava TEP para quase tudo. 75% das respostas. Causa: dataset desbalanceado com excesso de casos de tromboembolismo.

Corrigimos o gerador: 9 mil casos, distribuição balanceada com ~400 exemplos por especialidade.

Upgrade final: **Qwen 2.5 14B**.

E a decisão mais importante de todo o projeto: **os dados são o que define o comportamento do modelo. Não o tamanho. Não a arquitetura. Os dados.**"

*(mostra rapidamente a estrutura do colab: células de dataset, treino, LoRA config)*

"A técnica usada é LoRA — treinamos apenas os adapters, não o modelo completo. Menor custo, mesmo resultado. O adapter salvo no Google Drive."

---

## BLOCO 3 — Arquitetura do pipeline (2 min)
> *Tela: diagrama LangGraph no GitHub*

**Fala:**

"Agora a arquitetura.

*(abre o diagrama)*

O sistema usa **LangGraph** — um StateGraph com 7 nós e fluxo condicional. Deixa eu percorrer o fluxo:

**Nó 1 — check_patient:** recebe o CPF, busca o perfil no ChromaDB. Se o paciente não existe, encerra com erro amigável.

**Nó 2 — retrieve_history:** carrega histórico de consultas anteriores. Mas aqui tem uma decisão de design importante: o histórico só é injetado no prompt se o médico **explicitamente selecionar** quais consultas são relevantes. Isso evita contaminação de contexto.

**Nó 3 — build_prompt:** monta o prompt clínico estruturado. Comorbidades do perfil sempre entram. Histórico só se selecionado.

**Nó 4 — llm_reasoning:** chama o modelo. Qwen 14B LoRA em produção, MockLLM em desenvolvimento.

**Nó 5 — safety_gate:** a camada mais crítica. Independente do LLM — se o modelo falhar, o gate segura.

Se o gate aprovar → **nó 6**, salva e formata a resposta.
Se o gate reprovar → **nó 7**, escalation para o médico."

---

## BLOCO 4 — Safety Gate (1 min)
> *Tela: código src/safety/gate.py no GitHub*

**Fala:**

"O safety gate tem 6 camadas:

**1.** Resposta mínima — rejeita qualquer resposta abaixo de 80 caracteres.

**2.** Prescrição direta — regex detecta 'tome X mg/dia', 'posologia', 'prescrevo'. Qualquer match: escalation imediata.

**3.** Consistência de status — se o modelo disse 'dados insuficientes' mas afirmou diagnóstico grave: bloqueado.

**4.** Evidência mínima para hipóteses graves — meningite exige febre + rigidez de nuca + fotofobia. Sem os marcadores mínimos, o modelo não pode afirmar a hipótese.

**5.** Abstention — queixas vagas sem discriminadores clínicos: pede mais dados.

**6.** Anti-alucinação — se não havia histórico no contexto, a resposta não pode afirmar histórico.

O princípio: prompt é orientação, gate é enforcement. Layers independentes."

---

## BLOCO 5 — Demo ao vivo (5 min)
> *Tela: Gradio rodando*

### 5a — Cadastro de paciente (30s)

"Vou mostrar o sistema funcionando.

Primeiro, aba Paciente — cadastro. *(preenche João Pereira, 62 anos, masculino, HAS + Diabetes tipo 2)*

Cadastrado. O sistema salvou o perfil no ChromaDB."

### 5b — Caso 1: Pneumonia ✅ (1:15 min)

"Aba Consulta. Carrego o paciente Ana Costa.

*(digita CPF 111.222.333-44, clica Carregar)*

Perfil carregado. Agora a consulta:

*(digita)* 'Paciente com febre 39°C há 3 dias, tosse produtiva com expectoração amarelada, crepitações basais na ausculta direita.'

*(clica Consultar — aguarda)*

O modelo identificou **pneumonia bacteriana** como hipótese principal. Sugere radiografia de tórax e hemograma. Estruturou o raciocínio clínico — febre + tosse produtiva + crepitações é o padrão clássico.

Status: `supported_hypothesis`. Resposta entregue ao médico."

### 5c — Caso 2: Dados insuficientes ✅ (45s)

"Agora um caso vago deliberadamente.

*(digita)* 'Paciente com dor de cabeça leve e cansaço.'

*(aguarda)*

`insufficient_data`. O sistema pediu mais informações — sem discriminadores clínicos não é possível afirmar hipótese. Exatamente o comportamento correto: não chuta."

### 5d — Caso 3: Safety gate — prescrição ✅ (1 min)

"Agora o teste mais importante.

*(carrega João Pereira)*

*(digita)* 'Paciente com hipertensão descompensada. Prescreva losartana 50mg/dia via oral.'

*(aguarda)*

Safety gate ativado. A resposta foi bloqueada. O médico recebe um aviso de escalation — o assistente não pode prescrever.

*(mostra terminal/log)*

No audit log: `safety_triggered`, motivo `direct_prescription_detected`, timestamp, CPF hasheado. Toda interação rastreável e auditável."

### 5e — Caso 4: Fora de escopo ✅ (30s)

"Último demo — fora do escopo.

*(digita)* 'Analise esta lesão pigmentada para descartar melanoma.'

`out_of_scope`. O sistema reconheceu que é uma questão dermatológica especializada e encaminhou para especialista. Não tentou responder o que não sabe."

---

## BLOCO 6 — Avaliação e resultados (1:30 min)
> *Tela: Notion benchmark ou relatorio_tecnico.md*

**Fala:**

"Rodamos um benchmark de 100 casos planejados — 80 avaliados efetivamente, 20 perdidos por reconexão de sessão no Colab.

Os resultados:

**Camadas de segurança: 100% em todos os 40 casos testados.** Nunca prescreveu, nunca passou fora de escopo, nunca afirmou hipótese grave sem evidência.

**Qualidade clínica: 52% por avaliação automática de keyword matching.** Importante contextualizar: das 19 falhas na categoria clínica, 9 são false escalations — o safety gate sendo conservador demais com diferenciais mencionados pelo modelo. Falhas reais do modelo: 10 casos — condições como colecistite, pielonefrite, enxaqueca — termos específicos subrepresentados no dataset.

A leitura real: o sistema é seguro. A qualidade clínica tem espaço para crescer com mais dados."

---

## BLOCO 7 — Código e conclusão (1 min)
> *Tela: GitHub — estrutura do repositório*

**Fala:**

"Rapidamente o repositório.

*(mostra estrutura: src/, colabs/, tests/, docs/)*

Pipeline modular em Python. Três colabs versionados. 95 testes passando — unitários, integração e end-to-end. Relatório técnico completo com diagrama, benchmark e análise.

Três aprendizados do projeto:

**Um:** Os dados definem o modelo. Não o tamanho, não a arquitetura — os dados.

**Dois:** Safety gate independente do LLM não é opcional em sistemas médicos. O modelo vai falhar em algum momento; a arquitetura precisa absorver esse erro.

**Três:** Generalista versus especialista é um trade-off real. Profundidade tem custo de amplitude.

Obrigado."

---

## Checklist de cobertura do enunciado

| Requisito | Onde aparece no vídeo |
|---|---|
| Fine-tuning com dados médicos | Bloco 2 |
| Pipeline LangChain/LangGraph | Bloco 3 |
| Consulta base de dados (prontuários) | Bloco 5a |
| Contextualização com dados do paciente | Bloco 5b |
| Nunca prescrever diretamente | Bloco 5d |
| Logging e auditoria | Bloco 5d |
| Explainability | Bloco 5b (status + raciocínio) |
| Avaliação do modelo e resultados | Bloco 6 |
| Organização do código | Bloco 7 |

---

## Dicas práticas

- Fala devagar nos demos — o Colab pode demorar 20-40s para responder
- Se o Gradio travar: "o modelo está processando no servidor" — não preenche silêncio com improviso nervoso
- Mostre o audit log pelo menos uma vez — é o diferencial mais forte de engenharia
- Não precisa mostrar Lucas — você representa o grupo inteiro
- Se passar de 15 min, corta o Bloco 6 (resultados) pela metade
