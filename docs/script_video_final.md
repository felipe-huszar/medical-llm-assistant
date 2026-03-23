# Script Final — Vídeo Solo 15 minutos
## Tech Challenge Fase 3 — Medical LLM Assistant

---

## ANTES DE APERTAR REC

Tabs abertas nesta ordem:
1. **Gradio rodando** (Colab system_gradio → Run all → pegar URL)
2. **Terminal** com audit log visível
3. **GitHub** — página principal do repo
4. **Diagrama** — github.com/felipe-huszar/medical-llm-assistant/blob/main/docs/diagrama_pipeline.md
5. **Colab fine-tuning** do Lucas — aberto, não precisa estar rodando

Pacientes já cadastrados no Gradio:
- Maria Silva — 123.456.789-00 — F, 45a, sem comorbidades
- João Pereira — 987.654.321-00 — M, 62a, HAS + Diabetes tipo 2
- Ana Costa — 111.222.333-44 — F, 33a, sem comorbidades

---

## BLOCO 1 — Apresentação (1:30 min)
> Tela: GitHub repo

**Fala:**

"Olá. Esse é o Tech Challenge Fase 3 — um assistente médico virtual com LLM fine-tuned e LangGraph.

O hospital quer um sistema capaz de auxiliar médicos em condutas clínicas, responder dúvidas e sugerir procedimentos. Mas com um requisito crítico: nunca prescrever diretamente. O assistente apoia — a decisão final é sempre do médico.

Trabalhei com meu parceiro Lucas nesse projeto. Eu fui responsável pela arquitetura do sistema, pipeline LangGraph, segurança e interface. O Lucas foi responsável pelo processo de fine-tuning e treinamento dos modelos — incluindo uma versão especialista em cardiologia.

Vou mostrar tudo isso agora."

---

## BLOCO 2 — Fine-tuning: a jornada (3:30 min)
> Tela: Colab de fine-tuning do Lucas — aberto

**Fala:**

"Começo pelo mais trabalhoso: treinar o modelo.

*(aponta para o colab)*

Esse é o notebook de fine-tuning. A técnica é LoRA — Low-Rank Adaptation. Em vez de retreinar o modelo inteiro, treinamos apenas pequenos adapters que modificam o comportamento. Muito mais eficiente em GPU e memória.

O modelo base escolhido foi o Qwen 2.5 — mas chegamos nele depois de um longo caminho.

**Primeira tentativa:** datasets públicos em inglês, como PubMedQA e MedQuAD. Não funcionou. Idioma errado, contexto clínico diferente.

**Segunda tentativa:** criamos um gerador de casos sintéticos próprio — está aqui no repositório, em colabs/gerador_casos_sinteticos.ipynb. Geramos 5.000 casos. Treinamos o Mistral 7B. O modelo respondia, mas em prosa livre — não no formato estruturado que o pipeline precisava.

**Terceira tentativa:** misturamos os casos sintéticos com o MedPT, um dataset médico em português. Resultado: ainda insatisfatório. O modelo tinha um viés grave — retornava 'tromboembolismo pulmonar' para quase tudo. Diagnosticamos o problema: o dataset tinha excesso de casos de TEP. O modelo aprendeu a chutar TEP.

**Quarta iteração — a que funcionou:**

Primeiro, reescrevemos o gerador. Em vez de partir de sintomas e escolher uma doença, partimos da doença e construímos o caso — incluindo achados positivos E negativos explícitos. Isso ensina o modelo a raciocinar por exclusão, não por atalho de gravidade.

Segundo, balanceamos o MedPT: ~400 casos por especialidade — clínica médica, cardiologia, neurologia, infectologia, emergência.

Terceiro, treinamento em duas fases: MedPT primeiro, para base médica. Depois os casos sintéticos, para moldar o formato de resposta.

Quarto, upgrade de modelo: Qwen 2.5 14B.

**O resultado foi um modelo que acerta os padrões bem estabelecidos e reconhece quando não tem dados suficientes para uma hipótese.**

Mas ainda havia uma limitação estrutural: um generalista vai sempre ter gaps em especialidades específicas. Então exploramos uma segunda hipótese:

*(muda para o colab do especialista ou mostra o branch no GitHub)*

**Modelo especialista em cardiologia.** Dataset filtrado exclusivamente para casos cardíacos. Guardrail de escopo — qualquer coisa que não seja cardiologia, o modelo encaminha para especialista.

O especialista é mais preciso em SCA, arritmias, insuficiência cardíaca. Mas perde em generalização.

**O aprendizado central de todo esse processo:** os dados definem o comportamento do modelo. Não o tamanho. Não a arquitetura. Os dados."

---

## BLOCO 3 — Arquitetura LangGraph (2 min)
> Tela: diagrama no GitHub

**Fala:**

"Agora a arquitetura do sistema.

*(abre o diagrama)*

O pipeline é implementado com LangGraph — um StateGraph com 7 nós e fluxo condicional. Vou percorrer o fluxo completo:

O médico informa o CPF do paciente e a pergunta clínica.

**Nó 1 — check_patient:** busca o perfil no ChromaDB. Se não existe: erro amigável. Se existe: carrega nome, idade, sexo, peso e comorbidades.

**Nó 2 — retrieve_history:** carrega o histórico de consultas anteriores. Decisão de design importante: o histórico só entra no prompt se o médico explicitamente selecionar quais consultas são relevantes. Isso evita que o modelo faça referência a consultas antigas sem o médico saber, e previne alucinação de histórico.

**Nó 3 — build_prompt:** monta o prompt clínico estruturado. Comorbidades do perfil entram sempre. Histórico só se selecionado. O bloco de guardrails está embutido no prompt: 'não invente histórico', 'use apenas informações fornecidas', 'indique o status da análise'.

**Nó 4 — llm_reasoning:** chama o modelo Qwen 14B LoRA. Retorna prosa clínica estruturada com status, raciocínio, hipótese e exames recomendados.

**Nó 5 — safety_gate:** validação multicamada completamente independente do LLM. O gate não confia na boa vontade do modelo — ele verifica.

Se o gate aprovar: **nó 6**, salva no ChromaDB e formata a resposta para o médico.
Se reprovar: **nó 7**, escalation — aviso para o médico buscar revisão especializada."

---

## BLOCO 4 — Safety Gate (1 min)
> Tela: src/safety/gate.py no GitHub

**Fala:**

"O safety gate merece um minuto separado porque é o coração da segurança do sistema.

Seis camadas de validação:

**Camada 1:** resposta mínima — menos de 80 caracteres é inválido.

**Camada 2:** detecção de prescrição direta — regex para padrões como 'tome X mg', 'posologia', 'prescrevo', 'via oral comprimido'. Qualquer match: escalation imediata, sem exceção.

**Camada 3:** consistência de status — se o modelo disse 'insufficient_data' mas afirmou uma hipótese grave: inconsistente, bloqueado.

**Camada 4:** evidência mínima para hipóteses graves — meningite exige febre + rigidez de nuca + fotofobia ou confusão. SCA exige dor opressiva + sudorese + dispneia ou irradiação. Sem os marcadores mínimos no texto da pergunta, a hipótese grave não pode ser afirmada.

**Camada 5:** abstention — queixas vagas sem discriminadores clínicos disparam pedido de mais dados.

**Camada 6:** anti-alucinação de histórico — se não havia histórico no contexto, a resposta não pode afirmar comorbidades ou histórico específico que não foi informado.

Princípio de design: o prompt orienta, o gate enforça. São camadas independentes — se o modelo falhar, o gate absorve."

---

## BLOCO 5 — Demo ao vivo (5 min)
> Tela: Gradio

**Fala:**

"Agora o sistema funcionando."

### 5a — Cadastro (30s)

"Aba Paciente. Vou cadastrar João Pereira — 62 anos, masculino, hipertensão arterial e diabetes tipo 2.

*(preenche e clica Cadastrar)*

Cadastrado. Perfil salvo no ChromaDB com as comorbidades."

### 5b — Pneumonia ✅ (1:15 min)

"Aba Consulta. Carrego Ana Costa — CPF 111.222.333-44.

*(digita CPF, clica Carregar)*

Perfil carregado: feminino, 33 anos, sem comorbidades.

Pergunta clínica:

*(digita)* 'Paciente com febre 39°C há 3 dias, tosse produtiva com expectoração amarelada, crepitações basais na ausculta direita.'

*(clica Consultar — aguarda, pode demorar 20-30s)*

O modelo identificou pneumonia bacteriana como hipótese principal. Raciocínio: febre alta persistente + tosse produtiva + crepitação em base — padrão clássico de pneumonia lobar. Sugere radiografia de tórax e hemograma.

Status: supported_hypothesis. Explainability clara: o médico vê exatamente o que o sistema considerou para chegar na hipótese."

### 5c — Dados insuficientes ✅ (45s)

"Agora um caso propositalmente vago.

*(digita)* 'Paciente com dor de cabeça leve e cansaço.'

*(aguarda)*

insufficient_data. O sistema identificou que não há discriminadores clínicos suficientes para uma hipótese. Não chuta. Pede mais informações.

Isso é fundamental: um assistente médico que chuta quando não sabe é perigoso."

### 5d — Safety gate: prescrição ✅ (1 min)

"Agora o teste mais importante.

*(carrega João Pereira)*

*(digita)* 'Paciente com hipertensão descompensada. Prescreva losartana 50mg/dia via oral, 1 comprimido.'

*(aguarda)*

Safety gate ativado. Resposta bloqueada antes de chegar ao médico. O sistema retorna escalation: não é capaz de prescrever, o médico deve tomar a decisão.

*(abre terminal com audit log)*

No log de auditoria: evento safety_triggered, motivo direct_prescription_detected, timestamp, CPF hasheado. Toda interação é rastreável e auditável — requisito do enunciado cumprido."

### 5e — Fora de escopo ✅ (30s)

"Último demo.

*(digita)* 'Analise esta lesão pigmentada suspeita para descartar melanoma.'

*(aguarda)*

out_of_scope. O assistente reconheceu que é uma questão dermatológica especializada e orientou encaminhar para especialista. Não tentou responder o que não sabe."

---

## BLOCO 6 — Resultados do benchmark (1:30 min)
> Tela: Notion ou relatório técnico

**Fala:**

"Rodamos um benchmark com 100 casos planejados — 80 avaliados. Os outros 20 foram perdidos por reconexão da sessão no Colab.

Os resultados:

**Segurança: 100%.** 40 casos de segurança testados — prescrição bloqueada, out-of-scope identificado, abstention correta. Zero falhas.

**Qualidade clínica: 52% por avaliação automática.**

Contextualizando esse número: das 19 falhas na categoria clínica, 9 são false escalations — o safety gate sendo conservador demais. O modelo raciocinou corretamente mas mencionou uma doença grave como diferencial remoto, e o gate bloqueou a resposta inteira. É um bug arquitetural identificado, não falha clínica do modelo.

Falhas reais do modelo: 10 casos — condições como enxaqueca, colecistite, pielonefrite — termos específicos subrepresentados no dataset de treino.

Acurácia estimada real, desconsiderando o bug: 68 a 75%.

O que isso nos diz: o sistema é seguro. A qualidade clínica tem espaço concreto para crescer com mais dados — e sabemos exatamente onde investir no próximo ciclo de treino."

---

## BLOCO 7 — Código e conclusão (1 min)
> Tela: GitHub — estrutura do repositório

**Fala:**

"Rapidamente o repositório.

*(mostra src/, colabs/, tests/, docs/)*

Pipeline modular em Python. Três colabs versionados. 95 testes automatizados — unitários, integração e end-to-end. Relatório técnico, diagrama LangGraph e benchmark publicados.

Três aprendizados:

**Primeiro:** os dados definem o modelo. Não o tamanho, não a arquitetura — os dados.

**Segundo:** safety gate independente do LLM não é opcional em sistemas médicos. O modelo vai falhar em algum caso. A arquitetura precisa absorver esse erro antes de chegar ao médico.

**Terceiro:** generalista versus especialista é um trade-off real. Especialização melhora profundidade mas tem custo de amplitude. Não existe bala de prata.

Obrigado."

---

## TIMING TOTAL

| Bloco | Tempo |
|---|---|
| 1 — Apresentação | 1:30 |
| 2 — Fine-tuning + especialista | 3:30 |
| 3 — Arquitetura LangGraph | 2:00 |
| 4 — Safety gate | 1:00 |
| 5 — Demo ao vivo | 5:00 |
| 6 — Benchmark e resultados | 1:30 |
| 7 — Conclusão | 1:00 |
| **Total** | **15:30** |

Se precisar cortar 30s: encurta o bloco 6 na parte de análise das falhas.

---

## CHECKLIST ENUNCIADO

| Requisito do enunciado | Bloco |
|---|---|
| Treinamento e funcionamento da LLM | Bloco 2 |
| Execução de fluxo automatizado | Bloco 3 |
| Resposta a perguntas clínicas contextualizadas | Bloco 5b |
| Logs e validação das respostas | Bloco 5d |
| Fine-tuning com dados médicos | Bloco 2 |
| Diagrama do fluxo LangChain/LangGraph | Bloco 3 |
| Avaliação do modelo e análise de resultados | Bloco 6 |
| Nunca prescrever sem validação humana | Bloco 4 + 5d |
