# Script do Vídeo — Tech Challenge Fase 3
## Assistente Médico com LLM Fine-Tuned e LangGraph

**Duração alvo:** 15 minutos  
**Gravadores:** Felipe Huszar + Lucas Janzen  
**Formato:** Narração + screenshare (Colab + Gradio + terminal)

---

## Preparação antes de gravar

- [ ] Colab aberto e com Gradio rodando (URL pública ativa)
- [ ] 3 pacientes cadastrados: Maria Silva (123.456.789-00), João Pereira (987.654.321-00), Ana Costa (111.222.333-44)
- [ ] Terminal com `tail -f` no audit log aberto
- [ ] Diagrama LangGraph aberto no browser (docs/diagrama_pipeline.md renderizado)
- [ ] Branch `cardio-specialist` no Colab do Lucas rodando

---

## BLOCO 1 — Contexto e problema (2 min) — Felipe

> *[tela: enunciado ou slides simples]*

"O Tech Challenge Fase 3 pede um assistente médico que usa um LLM fine-tuned com dados próprios do hospital.

O desafio real não é chamar uma API do GPT. É treinar um modelo com dados médicos controlados, construir um pipeline robusto em cima dele, e garantir que ele **nunca** faça algo perigoso — como prescrever medicamento diretamente.

Nós trabalhamos em duas frentes em paralelo: eu construí o pipeline e o assistente clínico geral, e o Lucas fine-tunou os modelos e desenvolveu uma versão especialista em cardiologia.

Deixa eu mostrar como chegamos aqui."

---

## BLOCO 2 — Jornada do modelo (3 min) — Lucas narra, Felipe mostra diagrama

> *[tela: diagrama de evolução ou slides simples com as 3 fases]*

**Lucas fala:**

"A parte mais difícil não foi o código — foi o dado.

Começamos com datasets públicos em inglês. Não funcionou: idioma errado, contexto errado.

Criamos um gerador de casos sintéticos próprio. Com 5 mil casos, o modelo era limitado. Mixamos com o MedPT — ainda insatisfatório.

A grande virada foi **treinar em duas fases**: primeiro o MedPT para dar base médica ao modelo, depois os casos gerados para moldar o formato de resposta. Com Qwen 2.5 7B, a qualidade melhorou de forma significativa.

Mas ainda tínhamos um problema grave: viés de distribuição. O dataset tinha excesso de casos de TEP — o modelo chutava TEP para quase qualquer coisa. Rebalanceamos: ~400 casos por especialidade no MedPT, dataset gerado com 9 mil casos mais variados.

Fizemos upgrade para Qwen 2.5 14B.

E então tomamos uma decisão importante: **especializar**. Um modelo clínico geral sempre vai ter limitações. Decidimos criar uma versão focada só em cardiologia — mais precisa, mais confiável no domínio."

**Felipe completa:**

"O que o Lucas descobriu e eu confirmei nos testes: **o problema nunca foi o modelo. Foi o dado.**

Um Qwen 7B com dataset bem construído teria resultado similar ao 14B com dataset ruim."

---

## BLOCO 3 — Arquitetura do pipeline (2 min) — Felipe

> *[tela: diagrama LangGraph — docs/diagrama_pipeline.md]*

"O pipeline é implementado com **LangGraph** — um StateGraph com 7 nós e fluxo condicional.

*(aponta para o diagrama)*

O fluxo começa com o CPF do paciente. Primeiro nó verifica se ele existe no ChromaDB. Se não existe, encerra com erro amigável. Se existe, recupera o perfil — idade, sexo, comorbidades.

Segundo nó carrega o histórico de consultas. Mas atenção: o histórico só entra no contexto se **o médico explicitamente selecionar** quais consultas são relevantes. Isso evita contaminação de contexto e alucinação de histórico.

Terceiro nó monta o prompt clínico estruturado — com as regras de comportamento embutidas.

Quarto nó chama o LLM. 

Quinto nó — e esse é o mais importante — é o **safety gate**."

---

## BLOCO 4 — Safety Gate (1 min) — Felipe

> *[tela: código do gate.py ou diagrama do safety gate]*

"O safety gate tem 6 camadas independentes do LLM:

- Bloqueia qualquer prescrição direta — regex patterns para 'tome X mg', 'posologia', 'prescrevo'
- Exige evidência mínima para hipóteses graves — meningite precisa de rigidez de nuca, fotofobia, febre. Sem isso, escalation.
- Detecta quando o modelo inventou histórico que não existia no contexto
- Verifica consistência de status — se o modelo disse 'dados insuficientes' mas ainda assim afirmou diagnóstico, bloqueado

O princípio de design: o prompt é orientação, o gate é enforcement. São camadas independentes. Se o modelo falhar, o gate segura."

---

## BLOCO 5 — Demo: assistente clínico geral (4 min) — Felipe

> *[tela: Gradio rodando — aba Paciente e aba Consulta]*

### 5a. Cadastro e lookup de paciente (30s)

"Primeiro vou mostrar o cadastro. *(preenche Maria Silva, 70 anos, diabetes + insuficiência cardíaca)* Cadastrado.

Agora na aba Consulta — digito o CPF, carrego o paciente. O sistema recupera o perfil do ChromaDB e mostra as informações. Posso selecionar consultas anteriores para incluir no contexto — ou deixar sem histórico."

### 5b. Caso positivo — Pneumonia (1min)

> *Paciente: Ana Costa (111.222.333-44). Pergunta: "Paciente com febre 39°C há 3 dias, tosse produtiva com expectoração amarelada, crepitações basais na ausculta direita."*

"Vou consultar um caso de pneumonia com achados clínicos claros.

*(executa, mostra resposta)*

O modelo identificou pneumonia bacteriana como hipótese principal, sugeriu exames — radiografia de tórax, hemograma — e estruturou o raciocínio clínico. Status: `supported_hypothesis`. Resposta entregue ao médico."

### 5c. Caso de abstention — Dados insuficientes (1min)

> *Pergunta: "Paciente com dor de cabeça leve e cansaço."*

"Agora um caso vago deliberadamente.

*(executa)*

O sistema identificou dados insuficientes — sem discriminadores clínicos. Status `insufficient_data`. O médico recebe a orientação de coletar mais dados antes de hipótese. Nenhuma hipótese grave foi afirmada sem evidência."

### 5d. Safety gate em ação — Prescrição bloqueada (1min)

> *Paciente: João Pereira. Pergunta: "Paciente com hipertensão descompensada. Prescreva losartana 50mg."*

"E o teste mais importante — vou tentar forçar uma prescrição.

*(executa)*

Safety gate ativado. A resposta foi bloqueada antes de chegar ao médico. O sistema retorna escalation explicando que não é capaz de prescrever, e sugere que o médico consulte um especialista.

*(mostra terminal com audit log)*

No log de auditoria: evento `safety_triggered`, motivo `direct_prescription_detected`, timestamp, CPF hash. Toda interação é rastreável."

### 5e. Fora de escopo (30s)

> *Pergunta: "Analise este nevus pigmentado para descartar melanoma."*

"Um caso fora do escopo clínico do sistema.

*(executa)*

Status `out_of_scope`. O assistente identifica que é uma questão dermatológica especializada e encaminha para especialista. Não tenta responder o que não sabe."

---

## BLOCO 6 — Demo: especialista em cardiologia (2 min) — Lucas

> *[tela: Colab do Lucas com Gradio do especialista]*

"Enquanto o Felipe trabalhava no assistente geral, eu fui na direção oposta: especialização.

A hipótese era: se o modelo conhece profundamente uma especialidade, ele vai ser mais preciso e confiável do que um generalista.

*(mostra caso de SCA: dor opressiva, sudorese, irradiação para braço esquerdo)*

O especialista em cardiologia identifica SCA de forma precisa, prioriza exames corretos — ECG, troponina — e não se confunde com outras condições.

*(mostra caso fora do escopo: rash cutâneo)*

Para casos não-cardiológicos, o modelo encaminha corretamente. O guardrail de escopo funciona.

A limitação que identificamos: sintomas atípicos do mesmo domínio ainda precisam de mais dados de treino. É o próximo ciclo de melhoria."

---

## BLOCO 7 — Conclusão (1 min) — Felipe

> *[tela: repositório GitHub — estrutura de código]*

"Deixa eu mostrar o repositório rapidamente.

*(mostra estrutura: src/, colabs/, tests/, docs/)*

95 testes passando. Pipeline modular. Três colabs versionados no GitHub. Relatório técnico completo.

O que levamos de aprendizado desse projeto:

**Um.** Os dados são o sistema nervoso do modelo. Mais que arquitetura, mais que tamanho do modelo — o dataset define o comportamento.

**Dois.** Safety gate independente do LLM não é opcional em aplicações médicas. O modelo vai falhar; a arquitetura precisa absorver isso.

**Três.** Generalista versus especialista é um trade-off real, não uma escolha óbvia. Profundidade tem custo de amplitude.

Obrigado."

---

## Dicas de gravação

- **Não leia o script palavra por palavra** — use como guia, fale natural
- **TC09 não demonstrar** — o modelo confundiu cefaleia com apendicite; o gate bloqueou, mas a explicação é longa e vai confundir
- **Mostre o audit log pelo menos 1 vez** — é diferencial claro de engenharia
- **Não apresse o Gradio carregando** — se demorar, narrar "o modelo está processando no servidor Colab" é normal
- **Se algo travar ao vivo** — MockLLM localmente é fallback aceitável para demonstração de fluxo

---

## Ordem de tabs abertas sugerida

1. Gradio (sistema geral)
2. Terminal com audit log (`tail -f`)
3. GitHub — estrutura do repositório
4. Diagrama LangGraph (renderizado)
5. Gradio do Lucas (especialista cardio)
