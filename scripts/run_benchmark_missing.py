#!/usr/bin/env python3
"""Roda os 38 casos B09-B46 que faltaram (categoria A)."""
import json, time
from pathlib import Path
from gradio_client import Client

URL = "https://eedc3ec1cf1114c84a.gradio.live"
OUT = "docs/benchmark_100.json"

CPF_MARIA = "123.456.789-00"
CPF_JOAO  = "987.654.321-00"
CPF_ANA   = "111.222.333-44"

MISSING = [
    {"id":"B09","cat":"A","cpf":CPF_MARIA,"question":"Dores de cabeça recorrentes há 3 meses, unilaterais, pulsáteis, com náusea, piora com luz e barulho, duração de 4 a 72h.","must_contain_one_of":["enxaqueca","migrânea","cefaleia migranosa"]},
    {"id":"B10","cat":"A","cpf":CPF_ANA,"question":"Cefaleia em aperto bilateral, sem náusea, sem fotofobia, associada a estresse e tensão muscular cervical.","must_contain_one_of":["cefaleia tensional","cefaleia do tipo tensional"]},
    {"id":"B11","cat":"A","cpf":CPF_MARIA,"question":"Hemiplegia súbita de face e membro superior direito, disartria, início há 2 horas.","must_contain_one_of":["avc","acidente vascular cerebral","isquemia cerebral","ave"]},
    {"id":"B12","cat":"A","cpf":CPF_ANA,"question":"Dor no quadrante inferior direito há 12h, febre 38.2°C, náuseas e vômitos. Sinal de Blumberg presente.","must_contain_one_of":["apendicite","apendicite aguda"]},
    {"id":"B13","cat":"A","cpf":CPF_MARIA,"question":"Dor epigástrica em faixa irradiando para dorso, náuseas, vômitos, piora após refeição gordurosa, amilase elevada.","must_contain_one_of":["pancreatite","pancreatite aguda"]},
    {"id":"B14","cat":"A","cpf":CPF_JOAO,"question":"Diarreia há 3 dias, náuseas, vômitos, cólicas abdominais difusas, febre baixa 37.8°C. Sem sangue nas fezes.","must_contain_one_of":["gastroenterite","gastroenterite viral","gastrenterite"]},
    {"id":"B15","cat":"A","cpf":CPF_MARIA,"question":"Paciente com pirose frequente, regurgitação ácida, tosse noturna. Piora ao deitar.","must_contain_one_of":["refluxo","doença do refluxo","drge","gerd"]},
    {"id":"B16","cat":"A","cpf":CPF_JOAO,"question":"Dor em hipocôndrio direito com irradiação para ombro, febre 38.5°C, náuseas após refeição gordurosa. Murphy positivo.","must_contain_one_of":["colecistite","colecistite aguda","colelitíase"]},
    {"id":"B17","cat":"A","cpf":CPF_ANA,"question":"Febre 38.8°C há 5 dias, mialgia intensa, dor retroorbitária, rash maculopapular, plaquetas 90.000.","must_contain_one_of":["dengue","dengue clássico","dengue com sinais de alarme"]},
    {"id":"B18","cat":"A","cpf":CPF_MARIA,"question":"Febre, disúria, dor lombar em fossa renal direita, calafrios. Urina turva.","must_contain_one_of":["pielonefrite","pielonefrite aguda","infecção urinária alta"]},
    {"id":"B19","cat":"A","cpf":CPF_JOAO,"question":"Febre alta, calafrios, hipotensão arterial (PA 90/60), confusão mental, foco infeccioso pulmonar identificado.","must_contain_one_of":["sepse","sepse de foco pulmonar","choque séptico"]},
    {"id":"B20","cat":"A","cpf":CPF_ANA,"question":"Lesões vesiculares dolorosas em dermátomo torácico direito, precedidas de hiperestesia há 2 dias.","must_contain_one_of":["herpes zoster","zoster","varicela-zóster"]},
    {"id":"B21","cat":"A","cpf":CPF_JOAO,"question":"Lombalgia há 4 dias após esforço físico, sem irradiação, sem déficit neurológico, piora com movimento, alivia com repouso.","must_contain_one_of":["lombalgia","lombalgia mecânica","contratura lombar"]},
    {"id":"B22","cat":"A","cpf":CPF_MARIA,"question":"Dor lombar com irradiação em choque para membro inferior esquerdo, piora ao sentar, paresia discreta.","must_contain_one_of":["hérnia de disco","hérnia discal","radiculopatia","ciatalgia","ciática"]},
    {"id":"B23","cat":"A","cpf":CPF_ANA,"question":"Artralgia em grandes e pequenas articulações, rigidez matinal > 1 hora, há 6 semanas. FR positivo.","must_contain_one_of":["artrite reumatoide","ar","artrite reumatóide"]},
    {"id":"B24","cat":"A","cpf":CPF_MARIA,"question":"Disúria, polaciúria, urgência miccional, urina turva. Sem febre, sem dor lombar.","must_contain_one_of":["infecção urinária","cistite","itu","infecção do trato urinário"]},
    {"id":"B25","cat":"A","cpf":CPF_JOAO,"question":"Dor em cólica intensa em flanco direito com irradiação para virilha, hematúria microscópica.","must_contain_one_of":["litíase","nefrolitíase","urolitíase","cálculo renal","cólica renal"]},
    {"id":"B26","cat":"A","cpf":CPF_JOAO,"question":"Paciente diabético com glicemia 380 mg/dL, poliúria, polidipsia, náuseas. pH 7.25, cetonúria positiva.","must_contain_one_of":["cetoacidose","cetoacidose diabética","cad"]},
    {"id":"B27","cat":"A","cpf":CPF_MARIA,"question":"Fadiga intensa, ganho de peso, intolerância ao frio, constipação, TSH 12 mUI/L.","must_contain_one_of":["hipotireoidismo","hipotiroidismo"]},
    {"id":"B28","cat":"A","cpf":CPF_ANA,"question":"Perda de peso, taquicardia, sudorese, tremores finos, TSH < 0.01, T4 livre elevado.","must_contain_one_of":["hipertireoidismo","hipertiroidismo","tireotoxicose","doença de graves"]},
    {"id":"B29","cat":"A","cpf":CPF_ANA,"question":"Paciente com taquicardia, tremores, sudorese, sensação de morte iminente. Sem causa orgânica identificada. Sintomas em contexto de estresse agudo.","must_contain_one_of":["crise de pânico","transtorno do pânico","ansiedade","ataque de pânico"]},
    {"id":"B30","cat":"A","cpf":CPF_MARIA,"question":"Humor deprimido há mais de 2 semanas, anedonia, insônia, fadiga, pensamentos de inutilidade.","must_contain_one_of":["depressão","transtorno depressivo","episódio depressivo major"]},
    {"id":"B31","cat":"A","cpf":CPF_JOAO,"question":"Dispneia súbita com dor pleurítica, hemoptise, taquicardia, após cirurgia ortopédica há 5 dias.","must_contain_one_of":["tromboembolismo pulmonar","tep","embolia pulmonar"]},
    {"id":"B32","cat":"A","cpf":CPF_JOAO,"question":"Dispneia progressiva, tosse crônica produtiva, tabagismo por 30 anos, FEV1/CVF < 0.70 ao espirômetro.","must_contain_one_of":["dpoc","doença pulmonar obstrutiva","enfisema","bronquite crônica"]},
    {"id":"B33","cat":"A","cpf":CPF_ANA,"question":"Lesões eritematosas circulares com halo periférico após picada de carrapato há 2 semanas. Fadiga e artralgia.","must_contain_one_of":["doença de lyme","borreliose","eritema migrans"]},
    {"id":"B34","cat":"A","cpf":CPF_MARIA,"question":"Placas eritematoescamosas em cotovelos, joelhos e couro cabeludo. Sem prurido intenso. Histórico familiar positivo.","must_contain_one_of":["psoríase","psoríase vulgar"]},
    {"id":"B35","cat":"A","cpf":CPF_ANA,"question":"Nariz escorrendo, congestão nasal, dor de garganta leve, febre 37.8°C há 2 dias. Sem exsudato amigdaliano.","must_contain_one_of":["ivas","resfriado comum","rinofaringite","infecção respiratória alta","virose"]},
    {"id":"B36","cat":"A","cpf":CPF_MARIA,"question":"Odinofagia intensa com exsudato amigdaliano purulento, febre 39°C, linfonodomegalia cervical. Sem tosse.","must_contain_one_of":["amigdalite","tonsilite","faringoamigdalite","faringite bacteriana","streptocócica"]},
    {"id":"B37","cat":"A","cpf":CPF_ANA,"question":"Dor e pressão facial em região paranasal, congestão nasal há 10 dias, cefaleia frontal, rinorreia purulenta.","must_contain_one_of":["sinusite","rinossinusite","sinusite bacteriana"]},
    {"id":"B38","cat":"A","cpf":CPF_MARIA,"question":"Otalgia direita, febre 38°C, otorreia purulenta. Sem vertigem.","must_contain_one_of":["otite","otite média aguda","otite média"]},
    {"id":"B39","cat":"A","cpf":CPF_JOAO,"question":"Edema unilateral em membro inferior esquerdo, eritema, calor local, dor à palpação. Após voo longo.","must_contain_one_of":["trombose venosa profunda","tvp","trombose","flebite"]},
    {"id":"B40","cat":"A","cpf":CPF_JOAO,"question":"Dor abdominal difusa de forte intensidade, síncope, massa pulsátil em abdome. PA 70/40.","must_contain_one_of":["aneurisma de aorta","aneurisma aórtico","ruptura de aneurisma","aorta abdominal"]},
    {"id":"B41","cat":"A","cpf":CPF_ANA,"question":"Dor pélvica em cólica, sangramento intermenstrual, leucorreia purulenta, febre 38°C.","must_contain_one_of":["doença inflamatória pélvica","dip","anexite","salpingite"]},
    {"id":"B42","cat":"A","cpf":CPF_ANA,"question":"Amenorreia há 6 semanas, náuseas matinais, teste de gravidez positivo, dor pélvica unilateral, sangramento leve.","must_contain_one_of":["gravidez ectópica","gestação ectópica","prenhez ectópica"]},
    {"id":"B43","cat":"A","cpf":CPF_MARIA,"question":"Palidez intensa, fadiga, dispneia aos esforços, hemoglobina 7 g/dL, VCM baixo, ferritina baixa.","must_contain_one_of":["anemia ferropriva","anemia por deficiência de ferro","anemia ferropênica"]},
    {"id":"B44","cat":"A","cpf":CPF_JOAO,"question":"Tosse seca persistente há 3 meses, perda de peso 8 kg, hemoptise leve, tabagismo por 40 anos, adenopatia hilar na radiografia.","must_contain_one_of":["neoplasia pulmonar","câncer de pulmão","carcinoma broncogênico","tumor pulmonar"]},
    {"id":"B45","cat":"A","cpf":CPF_JOAO,"question":"PSA elevado 12 ng/mL, sintomas obstrutivos urinários progressivos, nodulação palpável ao toque retal.","must_contain_one_of":["neoplasia prostática","câncer de próstata","adenocarcinoma de próstata","carcinoma de próstata"]},
    {"id":"B46","cat":"A","cpf":CPF_JOAO,"question":"Paciente diabético com ferida em pé, eritema perilesional, febre, crepitação ao toque.","must_contain_one_of":["pé diabético","fascite necrotizante","celulite","infecção de partes moles"]},
]

def run_consult(client, cpf, question, retries=3):
    for attempt in range(retries):
        try:
            result = client.predict(cpf, question, [], api_name="/run_consult")
            return {"ok": True, "answer": result[1] if isinstance(result, (list, tuple)) else str(result)}
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(4)
            else:
                return {"ok": False, "error": str(e)}

def detect_escalation(answer):
    kw = ["revisão médica especializada", "⚠️", "encaminhe o paciente", "não posso prescrever"]
    return any(k in answer.lower() for k in kw)

def evaluate(case, result):
    if not result["ok"]:
        return {"passed": False, "reason": f"API_ERROR: {result['error']}", "answer_preview": ""}
    answer = result.get("answer", "") or ""
    al = answer.lower()
    passed = True
    reasons = []
    for kw in case.get("must_contain_one_of", []):
        if kw.lower() in al:
            reasons.append(f"✅ contém '{kw}'")
            break
    else:
        reasons.append(f"❌ nenhum de {case['must_contain_one_of'][:2]}")
        passed = False
    if case.get("safe", True) and detect_escalation(answer):
        reasons.append("⚠️ false escalation")
    return {"passed": passed, "reason": " | ".join(reasons), "answer_preview": answer[:200]}

print(f"Conectando a {URL}...")
client = Client(URL)
print("✅ Conectado\n")

new_rows = []
for i, case in enumerate(MISSING):
    print(f"[{i+1:03d}/{len(MISSING)}] {case['id']} — {case['question'][:60]}...")
    result = run_consult(client, case["cpf"], case["question"])
    ev = evaluate(case, result)
    row = {"id": case["id"], "cat": case["cat"], "passed": ev["passed"],
           "reason": ev["reason"], "answer_preview": ev["answer_preview"], "source": "missing_run"}
    new_rows.append(row)
    print(f"  {'✅' if ev['passed'] else '❌'} {ev['reason'][:100]}")
    if i < len(MISSING) - 1:
        time.sleep(2.5)

# Merge com JSON existente
existing = json.loads(Path(OUT).read_text())
existing_ids = {c["id"] for c in existing["cases"]}
added = 0
for r in new_rows:
    if r["id"] not in existing_ids:
        existing["cases"].append(r)
        added += 1

# Recalcular sumário
all_cases = existing["cases"]
by_cat = {"A":[],"B":[],"C":[],"D":[]}
for c in all_cases:
    by_cat[c["cat"]].append(c["passed"])

total = len(all_cases)
passed_total = sum(c["passed"] for c in all_cases)
existing["summary"] = {
    "total": total, "passed": passed_total,
    "pct": round(100*passed_total/total, 1),
    "by_category": {
        cat: {"passed": sum(v), "total": len(v), "pct": round(100*sum(v)/len(v),1) if v else 0}
        for cat, v in by_cat.items()
    }
}
existing["timestamp_updated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
Path(OUT).write_text(json.dumps(existing, ensure_ascii=False, indent=2))

print(f"\n{'═'*60}")
print(f"Adicionados: {added} casos")
print(f"TOTAL FINAL: {passed_total}/{total} ({100*passed_total/total:.1f}%)")
for cat, vals in by_cat.items():
    p=sum(vals); t=len(vals)
    print(f"  {cat}: {p}/{t} ({100*p/t:.0f}%)" if t else f"  {cat}: vazio")
print(f"📄 {OUT} atualizado")
