# Diagrama do Pipeline — LangGraph

## Fluxo Principal

```mermaid
%%{init: {'theme': 'default', 'flowchart': {'curve': 'orthogonal'}}}%%
flowchart TD
    START([🚀 Início\nCPF + Pergunta Médica]):::start

    N1["🔍 check_patient\n──────────────\n• Busca CPF no ChromaDB\n• Carrega perfil do paciente\n• Flag: is_new_patient"]:::node

    N2["📋 retrieve_history\n──────────────\n• Busca últimas 5 consultas\n• Isolado em benchmark_mode\n• Retorna lista de consultas"]:::node

    N3["🧠 build_prompt\n──────────────\n• Monta contexto clínico\n• Injeta comorbidades\n• Histórico somente se\n  selecionado pelo médico\n• Adiciona guardrail block"]:::node

    N4["🤖 llm_reasoning\n──────────────\n• Chama LLM\n  (Qwen LoRA ou MockLLM)\n• Retorna prosa clínica\n• Registra no audit log"]:::node

    N5["🛡️ safety_gate\n──────────────\n• Valida comprimento mín.\n• Detecta prescrição direta\n• Verifica consistência status\n• Evidência mínima p/ graves\n• Detecta dados insuficientes\n• Bloqueia alucinação histórico"]:::safety

    SAFE{Seguro?}:::decision

    N6["✅ save_and_format\n──────────────\n• Extrai seções da prosa\n• Monta Markdown enriquecido\n• Persiste no ChromaDB\n• Retorna resposta ao médico"]:::ok

    N7["⚠️ escalation\n──────────────\n• Mensagem de bloqueio\n• Motivo explícito\n• Orientação ao médico"]:::warn

    END_OK([📤 Resposta Clínica\npara o Médico]):::endok
    END_ERR([📤 Alerta de\nEscalation]):::enderr

    START --> N1
    N1 --> N2
    N2 --> N3
    N3 --> N4
    N4 --> N5
    N5 --> SAFE
    SAFE -- "needs_escalation = False" --> N6
    SAFE -- "needs_escalation = True" --> N7
    N6 --> END_OK
    N7 --> END_ERR

    classDef start fill:#4ade80,stroke:#16a34a,color:#000,font-weight:bold
    classDef node fill:#60a5fa,stroke:#2563eb,color:#000
    classDef safety fill:#f97316,stroke:#ea580c,color:#000,font-weight:bold
    classDef decision fill:#fbbf24,stroke:#d97706,color:#000,font-weight:bold
    classDef ok fill:#34d399,stroke:#059669,color:#000
    classDef warn fill:#f87171,stroke:#dc2626,color:#000
    classDef endok fill:#4ade80,stroke:#16a34a,color:#000
    classDef enderr fill:#fca5a5,stroke:#ef4444,color:#000
```

---

## Safety Gate — Camadas de Validação

```mermaid
%%{init: {'theme': 'default'}}%%
flowchart LR
    IN(["LLM Response\n(raw_response)"]):::input

    C1{"Comprimento\n< 80 chars?"}:::check
    C2{"Prescrição\ndireta?"}:::check
    C3{"Status\nconsistente?"}:::check
    C4{"Evidência mínima\np/ hipótese grave?"}:::check
    C5{"Dados\ninsuficientes?"}:::check
    C6{"Histórico\nalucin ado?"}:::check

    ESC(["⚠️ ESCALATION\nneed s_escalation=True"]):::esc
    OK(["✅ PASS\nsafety_passed=True"]):::pass

    IN --> C1
    C1 -- "Sim" --> ESC
    C1 -- "Não" --> C2
    C2 -- "Sim" --> ESC
    C2 -- "Não" --> C3
    C3 -- "Falha" --> ESC
    C3 -- "OK" --> C4
    C4 -- "Falha" --> ESC
    C4 -- "OK" --> C5
    C5 -- "Falha" --> ESC
    C5 -- "OK" --> C6
    C6 -- "Falha" --> ESC
    C6 -- "OK" --> OK

    classDef input fill:#93c5fd,stroke:#3b82f6,color:#000
    classDef check fill:#fef08a,stroke:#eab308,color:#000
    classDef esc fill:#fca5a5,stroke:#ef4444,color:#000,font-weight:bold
    classDef pass fill:#86efac,stroke:#22c55e,color:#000,font-weight:bold
```

---

## Arquitetura Completa do Sistema

```mermaid
%%{init: {'theme': 'default'}}%%
flowchart TB
    subgraph UI ["Interface — Gradio (app.py)"]
        TAB1["👤 Tab Paciente\n(registro e lookup)"]
        TAB2["🩺 Tab Consulta\n(pergunta + histórico)"]
    end

    subgraph PIPELINE ["Pipeline LangGraph (src/graph/)"]
        direction LR
        P1["check_patient"] --> P2["retrieve_history"]
        P2 --> P3["build_prompt"]
        P3 --> P4["llm_reasoning"]
        P4 --> P5["safety_gate"]
        P5 --> P6["save_and_format"]
        P5 --> P7["escalation"]
    end

    subgraph LLM ["Camada LLM (src/llm/)"]
        L1["factory.py\n(USE_MOCK_LLM)"]
        L2["MockLLM\n(dev/test)"]
        L3["Qwen 14B LoRA\n(produção)"]
        L1 --> L2
        L1 --> L3
    end

    subgraph RAG ["RAG — ChromaDB (src/rag/)"]
        R1["patients\ncollection"]
        R2["consultations\ncollection"]
    end

    subgraph SAFETY ["Safety Gate (src/safety/gate.py)"]
        S1["Prescrição\ndireta"]
        S2["Evidência mínima\nhipóteses graves"]
        S3["Dados\ninsuficientes"]
        S4["Histórico\nalucinado"]
    end

    subgraph AUDIT ["Auditoria (src/audit/)"]
        A1["audit_log()\n(evento por nó)"]
    end

    subgraph FINETUNING ["Fine-Tuning (colabs/)"]
        F1["gerador_casos_sinteticos.ipynb\n(dataset disease-centric)"]
        F2["finetuning.ipynb\n(Qwen LoRA, single-stage)"]
        F1 --> F2
        F2 --> L3
    end

    TAB1 --> RAG
    TAB2 --> PIPELINE
    PIPELINE --> LLM
    PIPELINE --> RAG
    PIPELINE --> SAFETY
    PIPELINE --> AUDIT
```

---

## Fluxo de Dados — Construção do Prompt

```mermaid
%%{init: {'theme': 'default'}}%%
flowchart LR
    A["Perfil do Paciente\n(sexo, idade, peso)"] --> P
    B["Comorbidades\n(condições crônicas)"] --> P
    C["Histórico selecionado\n(opt-in pelo médico)"] --> P
    D["Guardrail Block\n(regras críticas)"] --> P
    E["Pergunta Clínica\n(médico)"] --> P

    P["build_prompt\n───────────\nContexto do paciente\nRegras críticas\nSintomas relatados"]

    P --> LLM["🤖 LLM\n(Qwen LoRA)"]
    LLM --> R["Resposta em Prosa\ncom seções estruturadas"]
```

---

*Diagramas gerados em: 2026-03-22*  
*Renderização: GitHub Markdown, Notion (com plugin Mermaid), ou [mermaid.live](https://mermaid.live)*
