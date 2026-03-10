"""
mock_llm.py - Deterministic mock LLM returning realistic medical JSON responses.
"""

import json
import re

# Canned responses keyed by symptom keywords
_RESPONSES = [
    {
        "keywords": ["abdomi", "intestin", "evacua", "diarreia", "fezes"],
        "response": {
            "possible_diagnoses": [
                "Síndrome do intestino irritável",
                "Doença de Crohn",
                "Colite ulcerativa",
            ],
            "recommended_exams": [
                "Colonoscopia",
                "Hemograma completo",
                "PCR (Proteína C-reativa)",
                "Calprotectina fecal",
            ],
            "reasoning": (
                "Com base nos sintomas de dores abdominais associadas à evacuação, "
                "o quadro sugere patologia inflamatória ou funcional do intestino. "
                "Recomenda-se investigação endoscópica e marcadores inflamatórios "
                "para diferenciar entre etiologias funcionais e orgânicas."
            ),
            "sources": ["Protocolo GI-2024", "UpToDate: Irritable Bowel Syndrome"],
            "confidence": 0.75,
            "recommendation_type": "analysis",
        },
    },
    {
        "keywords": ["cefaleia", "cabeça", "enxaqueca", "dor de cabeça", "migran"],
        "response": {
            "possible_diagnoses": [
                "Enxaqueca sem aura",
                "Cefaleia tensional",
                "Cefaleia em salvas",
            ],
            "recommended_exams": [
                "Ressonância magnética do crânio",
                "Avaliação oftalmológica",
                "Pressão arterial seriada",
            ],
            "reasoning": (
                "Quadro de cefaleia recorrente requer exclusão de causas secundárias "
                "antes do diagnóstico de cefaleia primária. Neuroimagem indicada em "
                "casos com sinais de alarme (início súbito, alteração de padrão, febre)."
            ),
            "sources": ["Protocolo Neurologia-2023", "ICHD-3 Classification"],
            "confidence": 0.78,
            "recommendation_type": "analysis",
        },
    },
    {
        "keywords": ["cardio", "coração", "peito", "chest", "dispneia", "falta de ar", "taquicardia"],
        "response": {
            "possible_diagnoses": [
                "Doença arterial coronariana",
                "Insuficiência cardíaca",
                "Arritmia cardíaca",
            ],
            "recommended_exams": [
                "ECG de repouso e esforço",
                "Ecocardiograma",
                "Troponina e BNP",
                "Holter 24h",
            ],
            "reasoning": (
                "Sintomas cardiovasculares exigem avaliação funcional e estrutural do coração. "
                "Marcadores de necrose miocárdica e peptídeos natriuréticos auxiliam no "
                "diagnóstico diferencial entre isquemia aguda e disfunção crônica."
            ),
            "sources": ["Diretriz SBC 2024", "AHA/ACC Guidelines"],
            "confidence": 0.72,
            "recommendation_type": "analysis",
        },
    },
    {
        "keywords": ["diabetes", "glicemia", "açúcar", "insulina", "polidipsia", "poliuria"],
        "response": {
            "possible_diagnoses": [
                "Diabetes mellitus tipo 2",
                "Diabetes mellitus tipo 1",
                "Pré-diabetes",
            ],
            "recommended_exams": [
                "Glicemia de jejum",
                "HbA1c",
                "TTGO (Teste de Tolerância à Glicose Oral)",
                "Função renal (creatinina, uréia)",
            ],
            "reasoning": (
                "O quadro clínico é sugestivo de distúrbio do metabolismo glicídico. "
                "HbA1c fornece controle glicêmico dos últimos 3 meses e é critério "
                "diagnóstico para DM segundo ADA 2024."
            ),
            "sources": ["ADA Standards of Care 2024", "SBD Diretrizes 2024"],
            "confidence": 0.82,
            "recommendation_type": "analysis",
        },
    },
]

_DEFAULT_RESPONSE = {
    "possible_diagnoses": [
        "Diagnóstico indeterminado — requer avaliação clínica presencial",
        "Síndrome inespecífica",
    ],
    "recommended_exams": [
        "Hemograma completo",
        "Bioquímica básica (glicemia, creatinina, sódio, potássio)",
        "Urina tipo I",
    ],
    "reasoning": (
        "Não foi possível identificar padrão sintomático específico com os dados fornecidos. "
        "Recomenda-se avaliação clínica presencial e exames de triagem básica."
    ),
    "sources": ["Protocolo Triagem Geral-2024"],
    "confidence": 0.45,
    "recommendation_type": "analysis",
}


class MockLLM:
    """Deterministic mock LLM for development and testing."""

    def invoke(self, prompt: str) -> str:
        """Match keywords in prompt and return a canned JSON response."""
        prompt_lower = prompt.lower()
        for entry in _RESPONSES:
            if any(kw in prompt_lower for kw in entry["keywords"]):
                return json.dumps(entry["response"], ensure_ascii=False)
        return json.dumps(_DEFAULT_RESPONSE, ensure_ascii=False)

    def __call__(self, prompt: str) -> str:
        return self.invoke(prompt)
