# Test Execution Guide - Medical LLM Assistant

## Overview
Test suite completo para o Medical LLM Assistant usando MockLLM.

## Test Structure

```
tests/
├── unit/                    # Testes unitários
│   └── test_safety_gate.py  # Regras de segurança
├── integration/             # Testes de integração
│   └── test_pipeline.py     # Pipeline LangGraph
└── e2e/                     # Testes end-to-end
    ├── test_full_journeys.py      # Jornadas completas
    ├── test_pipeline_e2e.py       # Pipeline E2E
    └── test_extended_e2e.py       # Casos extendidos (NOVO)
```

## Como Executar

### 1. Quick Test (Verificação Rápida)
```bash
cd /root/.openclaw/workspace/projects/tech-challenge-fase3
python3 quick_test.py
```

### 2. Testes Unitários
```bash
python -m pytest tests/unit -v
```

### 3. Testes de Integração
```bash
python -m pytest tests/integration -v
```

### 4. Testes E2E (Todos)
```bash
python -m pytest tests/e2e -v
```

### 5. Suite Completa
```bash
python -m pytest tests/ -v --tb=short
```

### 6. Com Relatório JSON
```bash
python run_tests.py
```

## Cobertura de Testes E2E Extendidos

### REQ-E2E-EXT-1: Edge Cases
- ✅ Empty CPF handling
- ✅ CPF with special characters
- ✅ Very long questions
- ✅ Medical abbreviations
- ✅ Patient names with accents

### REQ-E2E-EXT-2: Concurrent Patient Isolation
- ✅ Multiple patients isolated
- ✅ Same person different CPFs

### REQ-E2E-EXT-3: Complex Multi-Symptom Cases
- ✅ Cardio + metabolic
- ✅ GI + neuro
- ✅ Vague undefined symptoms

### REQ-E2E-EXT-4: Age-Specific Profiles
- ✅ Pediatric patient (5 years)
- ✅ Geriatric patient (85 years)
- ✅ Newborn patient (0 years)

### REQ-E2E-EXT-5: Boundary Confidence Values
- ✅ Confidence 0.39 → escalates
- ✅ Confidence 0.40 → passes
- ✅ Confidence 0.41 → passes
- ✅ Confidence 0.0 → escalates
- ✅ Confidence 1.0 → passes

### REQ-E2E-EXT-6: Malformed LLM Responses
- ✅ Invalid JSON → escalates
- ✅ Partial JSON → escalates
- ✅ Empty string → escalates
- ✅ JSON with extra text → escalates
- ✅ Null values handling

### REQ-E2E-EXT-7: Large History Performance
- ✅ 10 consultations
- ✅ History limit respected

### REQ-E2E-EXT-8: Unicode and Internationalization
- ✅ Japanese characters
- ✅ Arabic characters
- ✅ Emoji in questions
- ✅ Portuguese medical terms

### REQ-E2E-EXT-9: MockLLM Keyword Coverage
- ✅ All keyword categories tested
- ✅ Unknown keywords default response

### REQ-E2E-EXT-10: Pipeline State Validation
- ✅ State evolution through nodes
- ✅ Patient profile in state

## Total de Testes

| Suite | Testes |
|-------|--------|
| Unit | 13 |
| Integration | 12 |
| E2E Core | 10 |
| E2E Pipeline | 11 |
| E2E Extended | 32 |
| **Total** | **~78** |

## Ambiente

- Model: MockLLM
- Database: ChromaDB (isolated per test)
- Environment: USE_MOCK_LLM=true

## Resultados Esperados

Todos os testes devem passar com MockLLM pois as respostas são determinísticas.
