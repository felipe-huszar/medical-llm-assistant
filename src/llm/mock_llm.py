"""
mock_llm.py - Mock LLM retornando respostas em prosa no formato clínico (Lucas format).
"""

import re

# Respostas em prosa por palavras-chave de sintomas
_RESPONSES = [
    {
        "keywords": ["abdomi", "intestin", "evacua", "diarreia", "fezes"],
        "response": """Resumo clínico:
Paciente apresentando sintomas gastrointestinais com dor abdominal relacionada à evacuação.

Raciocínio clínico:
Quadro sugere patologia inflamatória ou funcional do intestino. A ausência de sangramento nas fezes e o caráter crônico apontam para etiologia funcional, mas causas orgânicas devem ser excluídas.

Hipótese diagnóstica principal:
Síndrome do intestino irritável

Diagnósticos diferenciais:
- Doença de Crohn
- Colite ulcerativa
- Doença celíaca

Exames recomendados:
- Colonoscopia com biópsia
- Hemograma completo
- PCR (Proteína C-reativa)
- Calprotectina fecal""",
    },
    {
        "keywords": ["cefaleia", "cabeça", "enxaqueca", "dor de cabeça", "migran"],
        "response": """Resumo clínico:
Paciente com quadro de cefaleia recorrente.

Raciocínio clínico:
Necessário excluir causas secundárias antes do diagnóstico de cefaleia primária. Neuroimagem indicada em casos com sinais de alarme: início súbito em trovoada, alteração de padrão, febre ou déficit neurológico associado.

Hipótese diagnóstica principal:
Enxaqueca sem aura

Diagnósticos diferenciais:
- Cefaleia tensional
- Cefaleia em salvas
- Hipertensão intracraniana

Exames recomendados:
- Ressonância magnética do crânio
- Avaliação oftalmológica
- Pressão arterial seriada""",
    },
    {
        "keywords": ["cardio", "coração", "peito", "dispneia", "falta de ar", "taquicardia", "edema", "fadiga"],
        "response": """Resumo clínico:
Paciente com sintomas cardiovasculares de dispneia progressiva e edema.

Raciocínio clínico:
Dispneia progressiva associada a edema periférico sugere comprometimento cardiopulmonar. A fadiga concomitante reforça hipótese de disfunção ventricular ou sobrecarga volêmica.

Hipótese diagnóstica principal:
Insuficiência cardíaca descompensada

Diagnósticos diferenciais:
- Tromboembolismo pulmonar
- Pneumonia bilateral
- Insuficiência renal crônica

Exames recomendados:
- Ecocardiograma
- BNP/NT-proBNP
- Radiografia de tórax
- ECG de repouso""",
    },
    {
        "keywords": ["diabetes", "glicemia", "açúcar", "insulina", "polidipsia", "poliuria"],
        "response": """Resumo clínico:
Paciente com sintomas sugestivos de distúrbio metabólico glicídico.

Raciocínio clínico:
A tríade clássica polidipsia, poliúria e perda de peso é altamente sugestiva de diabetes mellitus. HbA1c é o padrão ouro para diagnóstico e controle glicêmico.

Hipótese diagnóstica principal:
Diabetes mellitus tipo 2

Diagnósticos diferenciais:
- Diabetes mellitus tipo 1
- Pré-diabetes
- Diabetes insípido

Exames recomendados:
- Glicemia de jejum
- HbA1c
- TTGO (Teste de Tolerância à Glicose Oral)
- Função renal (creatinina, ureia)""",
    },
]

_DEFAULT_RESPONSE = """Resumo clínico:
Paciente com quadro clínico inespecífico necessitando avaliação complementar.

Raciocínio clínico:
Não foi possível identificar padrão sintomático específico com os dados fornecidos. Recomenda-se avaliação clínica presencial e exames de triagem básica.

Hipótese diagnóstica principal:
Síndrome inespecífica — requer avaliação presencial

Diagnósticos diferenciais:
- A definir conforme avaliação clínica
- Aguardar resultado de exames básicos

Exames recomendados:
- Hemograma completo
- Bioquímica básica (glicemia, creatinina, sódio, potássio)
- Urina tipo I"""


class MockLLM:
    """Mock LLM determinístico retornando prosa no formato clínico."""

    def invoke(self, prompt: str) -> str:
        """Busca keywords na pergunta atual."""
        # Extrai apenas a pergunta atual
        marker = "Sintomas relatados:"
        if marker in prompt:
            question_text = prompt.split(marker, 1)[1]
        else:
            # Fallback para marcador antigo
            marker2 = "## Pergunta do Médico"
            question_text = prompt.split(marker2, 1)[1] if marker2 in prompt else prompt

        question_lower = question_text.lower()
        for entry in _RESPONSES:
            if any(kw in question_lower for kw in entry["keywords"]):
                return entry["response"]
        return _DEFAULT_RESPONSE

    def __call__(self, prompt: str) -> str:
        return self.invoke(prompt)
