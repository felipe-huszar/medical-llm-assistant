#!/usr/bin/env python3
"""Quick test to verify environment and imports."""

import sys
import os

project_root = "/root/.openclaw/workspace/projects/tech-challenge-fase3"
os.chdir(project_root)
sys.path.insert(0, project_root)

os.environ["USE_MOCK_LLM"] = "true"
os.environ["CHROMA_DB_PATH"] = "/tmp/chroma_test_quick"

print("Testing imports...")
try:
    from src.llm.mock_llm import MockLLM
    print("✅ MockLLM imported")
    
    from src.graph.pipeline import build_graph, run_consultation
    print("✅ Pipeline imported")
    
    from src.rag.patient_rag import save_patient, get_patient
    print("✅ RAG imported")
    
    from src.safety.gate import validate_response
    print("✅ Safety gate imported")
    
    print("\nTesting MockLLM...")
    llm = MockLLM()
    response = llm.invoke("dor abdominal")
    print(f"✅ MockLLM response: {response[:100]}...")
    
    print("\nTesting pipeline...")
    result = run_consultation(
        cpf="TEST.001",
        doctor_question="Paciente com dor abdominal.",
        patient_profile={"nome": "Test", "idade": 35, "sexo": "M", "peso": 70},
    )
    print(f"✅ Pipeline completed")
    print(f"   - Safety passed: {result['safety_passed']}")
    print(f"   - Needs escalation: {result['needs_escalation']}")
    print(f"   - Final answer length: {len(result['final_answer'])} chars")
    
    print("\n✅ ALL QUICK TESTS PASSED")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
