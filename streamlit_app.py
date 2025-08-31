import streamlit as st
import pandas as pd
import ast
import re

st.set_page_config(page_title="Test Case Değerlendirme", layout="wide")

# --- Yardımcı Fonksiyonlar ---
def parse_manual_test_steps(cell):
    """Manual Test Steps alanını Action/Data/Expected olarak ayırır"""
    if pd.isna(cell):
        return []
    try:
        steps = ast.literal_eval(cell)
        parsed = []
        for s in steps:
            parsed.append({
                "action": s.get("action", "").strip(),
                "data": s.get("data", "").strip(),
                "expected": s.get("expected", "").strip(),
            })
        return parsed
    except:
        return []

def detect_table_type(summary, steps):
    """Senaryo içeriğine göre tabloyu belirler (A/B/C/D)"""
    text = (summary or "").lower() + " ".join([s["action"] + s["data"] + s["expected"] for s in steps]).lower()

    needs_data = any("data:" in s["data"].lower() for s in steps)
    needs_precond = any("precondition" in text or "önkoşul" in text for s in steps)

    if needs_data and needs_precond:
        return "D"
    elif needs_precond:
        return "B"
    elif needs_data:
        return "C"
    else:
        return "A"

def score_test_case(row):
    """Her test case için tablo seçimi + kriter puanlaması"""
    key = row["Issue key"]
    summary = row["Summary"]
    steps = parse_manual_test_steps(row.get("Custom field (Manual Test Steps)", ""))

    table_type = detect_table_type(summary, steps)

    # Kriterler
    criteria = {
        "title": {"desc": "Test başlığı anlaşılır mı?", "ok": False, "score": 0},
        "priority": {"desc": "Öncelik bilgisi girilmiş mi?", "ok": False, "score": 0},
        "data": {"desc": "Test datası eklenmiş mi?", "ok": False, "score": 0},
        "precond": {"desc": "Test ön koşul eklenmiş mi?", "ok": False, "score": 0},
        "steps": {"desc": "Test stepleri var ve doğru ayrıştırılmış mı?", "ok": False, "score": 0},
        "client": {"desc": "Senaryonun hangi clientta koşulacağı belli mi?", "ok": False, "score": 0},
        "expected": {"desc": "Expected result bulunuyor mu?", "ok": False, "score": 0},
    }

    # Tablo puan değerleri
    if table_type == "A":
        weights = {"title":20,"priority":20,"steps":20,"client":20,"expected":20}
    elif table_type == "B":
        weights = {"title":17,"priority":17,"precond":17,"steps":17,"client":17,"expected":17}
    elif table_type == "C":
        weights = {"title":17,"priority":17,"data":17,"steps":17,"client":17,"expected":17}
    else: # D
        weights = {"title":14,"priority":14,"data":14,"precond":14,"steps":14,"client":14,"expected":14}

    # --- Puanlama ---
    # Başlık
    if isinstance(summary, str) and summary.strip():
        criteria["title"]["ok"] = True
        criteria["title"]["score"] = weights["title"]
        # ufak dilbilgisi hatası → kırıntı indirimi
        if not summary.endswith((".", "?", "!")):
            criteria["title"]["score"] -= 2
    else:
        criteria["title"]["score"] = 1  # başlık yoksa bile 0 değil

    # Öncelik
    if isinstance(row.get("Priority"), str) and row["Priority"].strip():
        criteria["priority"]["ok"] = True
        criteria["priority"]["score"] = weights["priority"]

    # Data
    if "data" in weights:
        if any("data:" in s["data"].lower() for s in steps):
            criteria["data"]["ok"] = True
            criteria["data"]["score"] = weights["data"]

    # Önkoşul
    if "precond" in weights:
        if "precondition" in (row.get("Custom field (Manual Test Steps)") or "").lower():
            criteria["precond"]["ok"] = True
            criteria["precond"]["score"] = weights["precond"]

    # Stepler
    if steps:
        joined_actions = " ".join(s["action"] for s in steps).lower()
        if len(steps) == 1:
            criteria["steps"]["score"] = 1  # tek step → çok puan kır
        else:
            criteria["steps"]["ok"] = True
            criteria["steps"]["score"] = weights["steps"]
            if "select" in joined_actions and "click" in joined_actions:
                criteria["steps"]["score"] -= 3  # birleşik ama kabul edilebilir
    else:
        criteria["steps"]["score"] = 0

    # Client
    if any("ios" in s["action"].lower() or "android" in s["action"].lower() or "web" in s["action"].lower() for s in steps):
        criteria["client"]["ok"] = True
        criteria["client"]["score"] = weights["client"]

    # Expected
    if "expected" in weights:
        if any(s["expected"].strip() for s in steps):
            exp_texts = [s["expected"] for s in steps if s["expected"].strip()]
            if exp_texts:
                criteria["expected"]["ok"] = True
                criteria["expected"]["score"] = weights["expected"]
                if any("should" not in e.lower() and "olmalı" not in e.lower() for e in exp_texts):
                    criteria["expected"]["score"] -= 2

    total = sum(c["score"] for c in criteria.values())
    return table_type, criteria, total, key, summary

# --- Streamlit UI ---
st.title("📊 Test Case Değerlendirme Uygulaması")

uploaded = st.file_uploader("CSV yükle", type="csv")

if uploaded:
    df = pd.read_csv(uploaded)
    results = []
    for _, row in df.iterrows():
        table_type, criteria, total, key, summary = score_test_case(row)
        results.append({
            "Issue key": key,
            "Summary": summary,
            "Table": table_type,
            "Total Score": total,
            "Criteria": criteria
        })

    res_df = pd.DataFrame([{
        "Issue key": r["Issue key"],
        "Summary": r["Summary"],
        "Table": r["Table"],
        "Total Score": r["Total Score"]
    } for r in results])

    st.dataframe(res_df, use_container_width=True)

    for r in results:
        st.markdown(f"### 📝 {r['Issue key']} – {r['Summary']}")
        st.write(f"**Tablo Türü:** {r['Table']} | **Toplam Puan:** {r['Total Score']}")
        crit_table = []
        for c_key, c in r["Criteria"].items():
            if c["score"] > 0 or c_key in ["title","steps","expected"]:
                icon = "✅" if c["ok"] else "❌"
                crit_table.append([icon, c["desc"], c["score"]])
        crit_df = pd.DataFrame(crit_table, columns=["Durum","Kriter","Puan"])
        st.table(crit_df)
