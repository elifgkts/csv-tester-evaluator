# -*- coding: utf-8 -*-
# 📌 Test Case Evaluator v1.5 – "Hepsi C olmasın" fix + açıklamalı gerekçe + debug
import streamlit as st
import pandas as pd
import re
import time
import random

st.set_page_config(page_title="Test Case SLA", layout="wide")
st.title("📋 Test Case Kalite Değerlendirmesi")

st.markdown("""
Bu uygulama test caseleri **A/B/C/D** tablosuna göre **senaryo içeriğini analiz ederek** otomatik sınıflandırır ve 7 kritere göre puanlar.
- **Data puanı:** Sadece *Manual Test Steps* içinde **`Data:`** etiketi varsa verilir (değerlendirme kriteri).
- **Tablo seçimi:** Gerçekten **data/önkoşul gereksinimi** var mı diye içerik sinyallerine bakılır (etiket bağımsız).
""")

with st.expander("📌 Kurallar (özet)"):
    st.markdown("""
- **CSV ayraç:** `;`
- **Gerekli sütunlar:** `Issue key` (veya `Issue Key`), `Summary`, `Priority`, `Labels`, `Custom field (Manual Test Steps)`
- **Tablo mantığı (senaryoya göre):**
  - **A:** Data da önkoşul da gerekmiyor
  - **B:** Önkoşul gerekli
  - **C:** Data gerekli
  - **D:** Hem data hem önkoşul gerekli
- **Puanlar:** A=5×20, B=6×17, C=6×17, D=7×14
- **Step kırıntı kuralı:** Birleşik ama mantıklı gruplanmış adım → kırpılmış puan (10–15 gibi)
""")

top1, top2, top3 = st.columns([1,1,1])
sample_size = top1.slider("📌 Kaç test case değerlendirilsin?", 1, 100, 5)
fix_seed = top2.toggle("🔒 Fix seed (deterministik örnekleme)", value=False)
debug_mode = top3.toggle("🧪 Sınıflandırma debug bilgisi", value=False)

if "reroll" not in st.session_state:
    st.session_state.reroll = 0
if st.button("🎲 Yeniden örnekle"):
    st.session_state.reroll += 1

uploaded = st.file_uploader("📤 CSV yükle (`;` ayraçlı)", type="csv")

# ---------- Yardımcılar ----------
def _text(x): 
    return str(x or "")

def _match(pattern, text):
    return re.search(pattern, text, re.IGNORECASE)

def has_data_tag(steps_text:str) -> bool:
    # Data PUANLAMA için sadece "Data:" etiketi
    return bool(re.search(r'(?:^|\n|\r)\s*[-\s]*Data\s*:', steps_text or "", re.IGNORECASE))

def extract_first(text, key):
    # JSON benzeri içerikten "Key": "..." yakala
    m = re.search(rf'"{key}"\s*:\s*"(.*?)"', text or "", re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""

def scan_data_signals(text:str):
    """Data ihtiyacını işaret eden **güçlü** sinyallerin listesi."""
    t = (text or "").lower()
    signals = []
    # 1) SQL anahtarları
    if _match(r'\b(select|insert|update|delete)\b', t):
        signals.append("SQL")
    # 2) JSON body: hem json/body/payload geçsin, hem de tipik "key":"value" deseni olsun
    if _match(r'\b(json|payload|body|request|response|headers|content-type)\b', t) and _match(r'"\w+"\s*:\s*".+?"', t):
        signals.append("JSON body")
    # 3) Kimlik/alan adları (net data bağımlılığı)
    if _match(r'\b(msisdn|token|iban|imei|email|username|password|user[_\-]?id|subscriber)\b', t):
        signals.append("Kimlik alanı")
    # 4) POST/PUT/PATCH + body/payload birlikte
    if _match(r'\b(post|put|patch)\b', t) and _match(r'\b(body|payload)\b', t):
        signals.append("POST payload")
    # 5) Bilinen placeholder'lar (yalnız bilinen alan adlarıyla)
    if _match(r'<\s*(msisdn|token|iban|imei|email|username|password|user[_\-]?id)\s*>', t) or \
       _match(r'\{\s*(msisdn|token|iban|imei|email|username|password|user[_\-]?id)\s*\}', t):
        signals.append("Placeholder(ID)")
    return signals

def scan_precond_signals(text:str):
    """Önkoşul ihtiyacını işaret eden sinyallerin listesi."""
    t = (text or "").lower()
    signals = []
    if _match(r'\bprecondition\b|ön\s*koşul|given .*already', t): signals.append("Precondition ifadesi")
    if _match(r'\b(logged in|login|giriş yap(mış|ın)|authenticated|auth)\b', t): signals.append("Login/Auth")
    if _match(r'\b(subscription|abonelik)\b.*\b(aktif|var|existing)\b', t): signals.append("Abonelik aktif")
    if _match(r'\bexisting user|mevcut kullanıcı\b', t): signals.append("Mevcut kullanıcı/hesap")
    if _match(r'\b(seed|setup|config(ure|)|feature flag|whitelist|allowlist|role|permission)\b', t): signals.append("Ortam/Ayar/Yetki")
    return signals

def decide_data_needed(summary:str, steps_text:str):
    """Data gerçekten **gerekli mi?**
    - Eğer Data: etiketi **veya** Data alanı varsa → doğrudan GEREKLİ.
    - Aksi halde, güçlü sinyal sayısı ≥ 2 ise GEREKLİ (tek sinyal yetmez).
    """
    combined = (summary or "") + "\n" + (steps_text or "")
    data_field = extract_first(steps_text, "Data")
    data_tag = has_data_tag(steps_text)
    signals = scan_data_signals(combined)

    # Güçlü doğrudan göstergeler
    if data_tag or (data_field.strip() != ""):
        return True, ["DataTag/Field"] + signals, 999  # 999 = doğrudan gerekli

    # Eşik: en az 2 farklı güçlü sinyal
    score = len(set(signals))
    return score >= 2, signals, score

def decide_precond_needed(summary:str, steps_text:str):
    combined = (summary or "") + "\n" + (steps_text or "")
    signals = scan_precond_signals(combined)
    score = len(set(signals))
    return score >= 1, signals, score

def choose_table(summary, steps_text):
    """Tablo + gerekçe üretimi (eşikli, false-positive azaltılmış)."""
    data_needed, data_signals, data_score = decide_data_needed(summary, steps_text)
    pre_needed, pre_signals, pre_score = decide_precond_needed(summary, steps_text)

    if data_needed and pre_needed:
        table, base, active = "D", 14, [1,2,3,4,5,6,7]
    elif data_needed:
        table, base, active = "C", 17, [1,2,3,5,6,7]
    elif pre_needed:
        table, base, active = "B", 17, [1,2,4,5,6,7]
    else:
        table, base, active = "A", 20, [1,2,5,6,7]

    # Gerekçe metni
    data_part = f"Data: {'GEREKLİ' if data_needed else 'gereksiz'} (sinyal sayısı={data_score}; {', '.join(data_signals) or '—'})"
    pre_part  = f"Önkoşul: {'GEREKLİ' if pre_needed else 'gereksiz'} (sinyal sayısı={pre_score}; {', '.join(pre_signals) or '—'})"
    reason = f"{data_part} | {pre_part}"
    return table, base, active, reason, (data_needed, data_signals, data_score), (pre_needed, pre_signals, pre_score)

def score_one(row):
    key = _text(row.get('Issue key') or row.get('Issue Key'))
    summary = _text(row.get('Summary'))
    priority = _text(row.get('Priority')).lower()
    steps_text = _text(row.get('Custom field (Manual Test Steps)'))

    action = extract_first(steps_text, "Action")
    expected = extract_first(steps_text, "Expected Result")

    table, base, active, reason, data_dbg, pre_dbg = choose_table(summary, steps_text)

    pts, notes, total = {}, [], 0

    # 1) Başlık
    if 1 in active:
        if not summary or len(summary) < 10:
            pts['Başlık'] = 0; notes.append("❌ Başlık çok kısa")
        elif any(w in summary.lower() for w in ["test edilir", "kontrol edilir"]):
            pts['Başlık'] = max(base-3, 1); notes.append(f"🔸 Başlık zayıf ifade ({pts['Başlık']})"); total += pts['Başlık']
        else:
            pts['Başlık'] = base; notes.append("✅ Başlık anlaşılır"); total += base

    # 2) Öncelik
    if 2 in active:
        if priority in ["", "null", "none"]:
            pts['Öncelik'] = 0; notes.append("❌ Öncelik eksik")
        else:
            pts['Öncelik'] = base; notes.append("✅ Öncelik var"); total += base

    # 3) Data – sadece "Data:" etiketi varsa puan
    if 3 in active:
        if has_data_tag(steps_text):
            pts['Data'] = base; notes.append("✅ `Data:` etiketi var"); total += base
        else:
            pts['Data'] = 0; notes.append("❌ `Data:` etiketi yok (0)")

    # 4) Ön Koşul
    if 4 in active:
        precond_present = decide_precond_needed(summary, steps_text)[0]
        if precond_present:
            pts['Ön Koşul'] = base; notes.append("✅ Ön koşul belirtilmiş/ima edilmiş"); total += base
        else:
            pts['Ön Koşul'] = 0; notes.append("❌ Ön koşul eksik")

    # 5) Stepler – kırıntı mantığı
    if 5 in active:
        if not action.strip():
            pts['Stepler'] = 0; notes.append("❌ Stepler boş")
        elif any(x in action for x in [",", " ardından ", " sonra ", " ve "]):
            kırp = 5 if base >= 17 else 3
            pts['Stepler'] = max(base - kırp, 1); notes.append(f"🔸 Birleşik ama mantıklı ({pts['Stepler']})"); total += pts['Stepler']
        else:
            pts['Stepler'] = base; notes.append("✅ Stepler düzgün"); total += base

    # 6) Client
    if 6 in active:
        ck = ["android","ios","web","mac","windows","chrome","safari"]
        if any(c in summary.lower() for c in ck) or any(c in action.lower() for c in ck):
            pts['Client'] = base; notes.append("✅ Client bilgisi var"); total += base
        else:
            pts['Client'] = 0; notes.append("❌ Client bilgisi eksik")

    # 7) Expected
    if 7 in active:
        if not expected.strip():
            pts['Expected'] = 0; notes.append("❌ Expected result eksik")
        elif any(w in expected.lower() for w in ["test edilir","kontrol edilir"]):
            pts['Expected'] = max(base-3, 1); notes.append(f"🔸 Expected zayıf ifade ({pts['Expected']})"); total += pts['Expected']
        else:
            pts['Expected'] = base; notes.append("✅ Expected düzgün"); total += base

    out = {
        "Key": key,
        "Summary": summary,
        "Tablo": table,
        "Tablo Gerekçesi": reason,
        "Toplam Puan": total,
        **pts,
        "Açıklama": " | ".join(notes),
    }
    if debug_mode:
        out["__Data_debug__"] = f"{data_dbg}"
        out["__Pre_debug__"] = f"{pre_dbg}"
    return out

# ---------- Çalıştır ----------
if uploaded:
    # seed yönetimi (deterministik istenirse)
    if fix_seed:
        random.seed(20250831 + st.session_state.reroll)
    else:
        random.seed(time.time_ns())

    # CSV oku (önce ; sonra varsayılan)
    try:
        df = pd.read_csv(uploaded, sep=';')
    except Exception:
        df = pd.read_csv(uploaded)

    # Gerçek rastgele örnekleme
    if len(df) > sample_size:
        idx = random.sample(range(len(df)), sample_size)
        sample = df.iloc[idx].copy()
    else:
        sample = df.copy()

    results = sample.apply(score_one, axis=1, result_type='expand')

    st.markdown("### 📈 Tablo Dağılımı")
    dist = results['Tablo'].value_counts().sort_index()
    st.write({k:int(v) for k,v in dist.items()})

    st.markdown("## 📊 Değerlendirme Tablosu")
    st.dataframe(results.set_index("Key"))

    st.download_button(
        "📥 Sonuçları CSV olarak indir",
        data=results.to_csv(index=False, sep=';', encoding='utf-8'),
        file_name="testcase_skorlari.csv",
        mime="text/csv"
    )

    st.markdown("## 📝 Detaylar")
    for _, r in results.iterrows():
        st.markdown(f"### 🔍 {r['Key']} | {r['Summary']}")
        st.markdown(f"**Tablo:** `{r['Tablo']}` • **Toplam:** `{r['Toplam Puan']}`")
        st.markdown(f"**Neden bu tablo?** {r['Tablo Gerekçesi']}")
        if debug_mode:
            st.code(f"DATA_DEBUG = {r.get('__Data_debug__','')}\nPRE_DEBUG  = {r.get('__Pre_debug__','')}")
        for k in ['Başlık','Öncelik','Data','Ön Koşul','Stepler','Client','Expected']:
            if k in r and pd.notna(r[k]):
                st.markdown(f"- **{k}**: {int(r[k])} puan")
        st.markdown(f"🗒️ **Açıklamalar:** {r['Açıklama']}")
