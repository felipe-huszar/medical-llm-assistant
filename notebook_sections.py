"""
notebook_sections.py - Estrutura organizada do Colab em 6 seções independentes.

SEÇÃO 1: Setup e Dependências
- Git clone/pull
- Instalação de pacotes
- Verificação de GPU

SEÇÃO 2: Configuração
- Variáveis de ambiente (USE_MOCK, paths)
- Download do LoRA do Lucas
- Configuração do ChromaDB

SEÇÃO 3: Modelo (Independente)
- Carrega Mistral + LoRA
- Expondo API FastAPI na porta 8000
- NÃO depende das outras seções (só do Setup)

SEÇÃO 4: Banco de Dados
- Seed de pacientes
- Limpeza se necessário
- Validação

SEÇÃO 5: UI Gradio (Opcional)
- Só se quiser interface web no Colab
- Consome a API da Seção 3
- Pode rodar separadamente

SEÇÃO 6: Publicação
- Gist de testes
- Gist de audit log
- Validação final

Para usar:
1. Rode Seção 1 (sempre)
2. Rode Seção 2 (configura)
3. Escolha: Seção 3 (API) OU Seção 5 (UI local) ou ambas
4. Rode Seção 4 quando precisar resetar dados
5. Rode Seção 6 para publicar resultados
"""

# ============================================================================
# SEÇÃO 1: SETUP E DEPENDÊNCIAS (Sempre execute primeiro)
# ============================================================================

SECTION_1 = '''
# 1.1 Git - Atualiza código
!cd /content/medical-llm-assistant && git pull

# 1.2 Dependências
!pip install -q unsloth peft bitsandbytes accelerate gdown
!pip install -q chromadb langgraph gradio fastapi uvicorn pyngrok

# 1.3 Verificação GPU
import torch
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB" if torch.cuda.is_available() else "N/A")

# 1.4 Path do projeto
import sys
sys.path.insert(0, '/content/medical-llm-assistant')
print("✅ Setup completo")
'''

# ============================================================================
# SEÇÃO 2: CONFIGURAÇÃO
# ============================================================================

SECTION_2 = '''
import os

# Modo de operação
USE_MOCK = 'false'  # 'true' = MockLLM, 'false' = Mistral real

# Paths
CHROMA_DB_PATH = '/content/chroma_db'
LORA_PATH = '/content/model'

# Drive do Lucas (pasta pública com o LoRA)
LUCAS_FOLDER_ID = '1i7SbQDLxuGIPGheTHuAgYXUQ_ZU1vIN6'

# Configura ambiente
os.environ['USE_MOCK_LLM'] = USE_MOCK
os.environ['CHROMA_DB_PATH'] = CHROMA_DB_PATH
os.environ['MODEL_PATH'] = LORA_PATH

print(f"Modo: {'Mock' if USE_MOCK == 'true' else 'Mistral Real'}")
print(f"ChromaDB: {CHROMA_DB_PATH}")
print(f"LoRA: {LORA_PATH}")

# Download do LoRA (se modo real)
if USE_MOCK != 'true':
    import subprocess, glob, zipfile, os as os2
    os2.makedirs(LORA_PATH, exist_ok=True)
    
    result = subprocess.run(
        ['gdown', '--folder', f'https://drive.google.com/drive/folders/{LUCAS_FOLDER_ID}',
         '-O', LORA_PATH, '--remaining-ok'],
        capture_output=True, text=True
    )
    
    # Extrai ZIP se houver
    zips = glob.glob(f"{LORA_PATH}/*.zip")
    if zips:
        with zipfile.ZipFile(zips[0], 'r') as zf:
            zf.extractall(LORA_PATH)
        print(f"📦 Extraído: {zips[0]}")
    
    # Valida
    import os
    has_config = any('adapter_config.json' in f for r, d, f in os.walk(LORA_PATH))
    has_model = any('adapter_model.safetensors' in f for r, d, f in os.walk(LORA_PATH))
    
    if has_config and has_model:
        print("✅ LoRA baixado e validado")
    else:
        print("⚠️ Arquivos do LoRA não encontrados")
else:
    print("✅ Modo Mock - LoRA não necessário")
'''

# ============================================================================
# SEÇÃO 3: MODELO + API (Independente - só depende do Setup)
# ============================================================================

SECTION_3 = '''
# Esta célula sobe APENAS o modelo como API
# Você pode rodar isso e depois usar a UI local no Oracle

import os
import sys
sys.path.insert(0, '/content/medical-llm-assistant')

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from threading import Thread
import nest_asyncio
nest_asyncio.apply()

# Carrega modelo
print("🔄 Carregando modelo...")
from src.llm.factory import get_llm
from src.rag.patient_rag import get_patient
from src.graph.pipeline import run_consultation

_llm = get_llm()
print(f"✅ Modelo carregado: {type(_llm).__name__}")

# API
app_api = FastAPI(title="Medical LLM API")

class ConsultRequest(BaseModel):
    cpf: str
    question: str

@app_api.post("/consult")
def consult(req: ConsultRequest):
    """Endpoint principal de consulta médica."""
    profile = get_patient(req.cpf)
    if not profile:
        return {
            "error": "Paciente não encontrado",
            "cpf": req.cpf
        }
    
    result = run_consultation(
        cpf=req.cpf,
        doctor_question=req.question,
        llm=_llm,
        patient_profile=profile
    )
    
    return {
        "cpf": req.cpf,
        "profile": result.get("patient_profile"),
        "answer": result.get("final_answer"),
        "safety_passed": result.get("safety_passed"),
        "needs_escalation": result.get("needs_escalation")
    }

@app_api.get("/health")
def health():
    return {"status": "ok", "model": type(_llm).__name__}

# Expõe via ngrok
from pyngrok import ngrok
public_url = ngrok.connect(8000)
print(f"🌐 API URL: {public_url}")
print(f"   Health: {public_url}/health")
print(f"   Consult: {public_url}/consult")
print("\n💡 Copie a URL acima e cole no chat para o huszardoBot usar")

# Roda servidor
def run():
    uvicorn.run(app_api, host="0.0.0.0", port=8000)

Thread(target=run, daemon=True).start()
print("\n✅ API rodando em background")
'''

# ============================================================================
# SEÇÃO 4: BANCO DE DADOS (Seed e Limpeza)
# ============================================================================

SECTION_4 = '''
import os
import shutil
os.environ['CHROMA_DB_PATH'] = '/content/chroma_db'

import sys
sys.path.insert(0, '/content/medical-llm-assistant')

from src.rag.patient_rag import seed_from_file

# Opção A: Limpar e recriar
LIMPAR = False  # Mude para True para limpar

if LIMPAR and os.path.exists('/content/chroma_db'):
    shutil.rmtree('/content/chroma_db')
    print("🗑️ ChromaDB limpo")

# Seed de pacientes
n = seed_from_file('/content/medical-llm-assistant/data/patients_seed.json')
print(f"✅ {n} pacientes carregados")

# Lista pacientes
from src.rag.patient_rag import _get_client
client = _get_client()
collection = client.get_collection("patients")
print(f"📊 Total no DB: {collection.count()}")
'''

# ============================================================================
# SEÇÃO 5: UI GRADIO (Opcional - só se quiser interface no Colab)
# ============================================================================

SECTION_5 = '''
# Só execute se quiser usar a interface web diretamente no Colab
# Se estiver usando a API (Seção 3), pode pular esta

import os
import sys
sys.path.insert(0, '/content/medical-llm-assistant')
os.environ['CHROMA_DB_PATH'] = '/content/chroma_db'

from app import demo

demo.launch(
    share=True,  # Gera link público
    debug=True,
    show_error=True
)
'''

# ============================================================================
# SEÇÃO 6: PUBLICAÇÃO (Gist)
# ============================================================================

SECTION_6 = '''
# Publica resultados de testes no Gist

import json
import requests
import os
from datetime import datetime

GIST_ID = 'f3e6e10d65eff30560abf756467d8d1b'
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')  # Defina no secrets se necessário

# Lê audit log
audit_path = '/tmp/medical_audit.jsonl'
if os.path.exists(audit_path):
    with open(audit_path) as f:
        lines = [json.loads(l) for l in f if l.strip()]
    
    # Prepara conteúdo
    content = '\\n'.join(json.dumps(l, ensure_ascii=False) for l in lines[-50:])  # últimos 50
    
    # Atualiza Gist
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    data = {
        "files": {
            "audit_log.jsonl": {
                "content": content
            }
        }
    }
    
    resp = requests.patch(url, headers=headers, json=data)
    if resp.status_code == 200:
        print(f"✅ Audit log atualizado: https://gist.github.com/felipe-huszar/{GIST_ID}")
    else:
        print(f"⚠️ Erro: {resp.status_code}")
        print(resp.text)
else:
    print("⚠️ Audit log não encontrado")
'''

# Salva arquivo de referência
with open('/root/.openclaw/workspace/projects/tech-challenge-fase3/notebook_sections.py', 'w') as f:
    f.write(__doc__ + '\n\n')
    f.write('SECTION_1 = """' + SECTION_1 + '"""\n\n')
    f.write('SECTION_2 = """' + SECTION_2 + '"""\n\n')
    f.write('SECTION_3 = """' + SECTION_3 + '"""\n\n')
    f.write('SECTION_4 = """' + SECTION_4 + '"""\n\n')
    f.write('SECTION_5 = """' + SECTION_5 + '"""\n\n')
    f.write('SECTION_6 = """' + SECTION_6 + '"""\n')

print("Arquivo notebook_sections.py criado com as 6 seções")
