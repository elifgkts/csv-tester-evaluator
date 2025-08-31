import streamlit as st
import pandas as pd
import json
import random
import re

st.set_page_config(page_title="Test Case Değerlendirme", layout="wide")
st.title("📋 Test Case Kalite Değerlendirme Aracı")

# 7 kriter puanları tablolar bazında
TABLO_PUANLARI = {
    "A": {"summary": 20, "priority": 20, "steps": 20, "client": 20, "expected": 20},
    "B": {"summary": 17, "priority": 17, "precondition": 17, "steps": 17, "client": 17, "expected": 17},
    "C": {"summary": 17, "priority": 17, "testdata": 17, "steps": 17, "client": 17, "expected": 17},
    "D": {"summary": 14, "priority": 14, "testdata": 14, "precondition": 14, "steps": 14, "client": 14, "expected": 14},
}

# NLP destekli tablo belirleyici
def belirle_tablo(summary, steps_json):
    summary = summary.lower()
    steps_text = json.dumps(steps_json).lower()
    
    step_texts = [s.get("Action", "").lower() for s in steps_json]

    has_data = any(re.search(r"token|msisdn|account|data|payload|auth|config|header|mail|user", t) for t in step_texts)
    has_precondition = any(re.search(r"giriş yap|login ol|hesap oluştur|öncesinde|hazırlık|setup|bağlan", t) for t in step_texts)

    if has_data and has_precondition:
        return "D"
    elif has_precondition:
        return "B"
    elif has_data:
        return "C"
    else:
        return "A"

# JSON içindeki alanı ayıkla
def get_field(steps, field):
    try:
        if isinstance(steps, str):
            steps = json.loads(steps)
        return [step.get(field, "") for step in steps if isinstance(step, dict)]
    except:
        return []

# Kriterlere göre puanlama yap

def puanla(row):
    key = row["Issue key"]
    summary = row["Summary"]
    priority = row["Priority"]
    client = row["Custom field (Client Type)"]
    precond = row["Custom field (Tests association with a Pre-Condition)"]
    steps_raw = row["Custom field (Manual Test Steps)"]

    try:
        steps = json.loads(steps_raw)
    except:
        steps = []

    tablo = belirle_tablo(summary, steps)
    puanlar = TABLO_PUANLARI[tablo]
    total = 0
    açıklamalar = []

    def kırıntı_puan(puan, oran): return max(1, round(puan * oran))

    # Summary
    if not summary or summary.strip() == "":
        p = 0
        açıklama = "❌ Summary boş"
    elif re.search(r" gidilir$", summary.strip()):
        p = kırıntı_puan(puanlar["summary"], 0.75)
        açıklama = "⚠️ Summary var ama doğru ifade edilmemiş (örn. 'gidilmesi' olmalıydı)"
    else:
        p = puanlar["summary"]
        açıklama = "✅ Anlaşılır summary"
    total += p
    açıklamalar.append(f"- Summary ({p}/{puanlar['summary']}): {açıklama}")

    # Priority
    if priority:
        p = puanlar["priority"]
        açıklama = "✅ Priority girilmiş"
    else:
        p = 0
        açıklama = "❌ Priority boş"
    total += p
    açıklamalar.append(f"- Öncelik ({p}/{puanlar['priority']}): {açıklama}")

    # Precondition (gerekiyorsa)
    if "precondition" in puanlar:
        if precond and precond.strip():
            p = puanlar["precondition"]
            açıklama = "✅ Ön koşul belirtilmiş"
        else:
            p = 0
            açıklama = "❌ Ön koşul eksik"
        total += p
        açıklamalar.append(f"- Ön Koşul ({p}/{puanlar['precondition']}): {açıklama}")

    # Test Data (gerekiyorsa)
    if "testdata" in puanlar:
        data_fields = get_field(steps, "Data")
        if any(d.strip() for d in data_fields):
            p = puanlar["testdata"]
            açıklama = "✅ Test datası girilmiş"
        else:
            p = 0
            açıklama = "❌ Test datası eksik"
        total += p
        açıklamalar.append(f"- Test Data ({p}/{puanlar['testdata']}): {açıklama}")

    # Steps
    actions = get_field(steps, "Action")
    if len(actions) <= 1 or summary.strip().lower() in actions[0].lower():
        p = 1
        açıklama = "⚠️ Step alanına summary yazılmış veya tek adımda özetlenmiş"
    elif all(len(a.strip()) < 5 for a in actions):
        p = 0
        açıklama = "❌ Step içerikleri çok kısa"
    else:
        p = puanlar["steps"]
        açıklama = "✅ Step'ler ayrılmış ve anlamlı"
    total += p
    açıklamalar.append(f"- Stepler ({p}/{puanlar['steps']}): {açıklama}")

    # Client
    if client:
        p = puanlar["client"]
        açıklama = "✅ Client belirtilmiş"
    else:
        p = 0
        açıklama = "❌ Client eksik"
    total += p
    açıklamalar.append(f"- Client ({p}/{puanlar['client']}): {açıklama}")

    # Expected Result
    expecteds = get_field(steps, "Expected Result")
    if not any(e.strip() for e in expecteds):
        p = 0
        açıklama = "❌ Expected result eksik"
    elif any(re.search(r"test edilir|gözlemlenir|kontrol edilir", e.lower()) for e in expecteds):
        p = kırıntı_puan(puanlar["expected"], 0.75)
        açıklama = "⚠️ Expected Result var ama testin ne olduğu gibi yazılmış"
    else:
        p = puanlar["expected"]
        açıklama = "✅ Expected Result açık"
    total += p
    açıklamalar.append(f"- Expected Result ({p}/{puanlar['expected']}): {açıklama}")

    return pd.Series({
        "Issue Key": key,
        "Summary": summary,
        "Tablo": tablo,
        "Puan": total,
        "Açıklama": "\n".join(açıklamalar)
    })

# Arayüz
uploaded = st.file_uploader("Test Case CSV dosyasını yükleyin", type=["csv"])
if uploaded:
    df = pd.read_csv(uploaded, sep=";")
    örnekler = df.sample(min(5, len(df)))
    sonuçlar = örnekler.apply(puanla, axis=1)

    for _, row in sonuçlar.iterrows():
        with st.expander(f"🔎 {row['Issue Key']} – {row['Summary'][:70]}..."):
            st.markdown(f"""
            📌 **Tablo:** {row['Tablo']}  
            🎯 **Puan:** {row['Puan']} / 100

            {row['Açıklama']}
            """)
