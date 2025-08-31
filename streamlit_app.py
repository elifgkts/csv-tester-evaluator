import streamlit as st
import pandas as pd
import random
import re

st.set_page_config(page_title="Test Case Değerlendirici", layout="wide")
st.title("📋 Test Case Kalite Değerlendirmesi")
st.markdown("""
Bu uygulama, test caselerinizi **A, B, C veya D tablosuna** göre değerlendirir.
Her test case'in ait olduğu tablo, **senaryo içeriğine göre otomatik belirlenir** ve 7 kritere göre puanlama yapılır.
""")

with st.expander("📌 Değerlendirme Kuralları ve Kriter Açıklamaları"):
    st.markdown("""
**CSV formatı:** CSV dosyası `;` (noktalı virgül) ile ayrılmış olmalıdır.

**Gerekli sütunlar:**
- Issue Key
- Summary
- Priority
- Labels
- Custom field (Manual Test Steps)

**Tablo Seçimi (Senaryoya göre):**
- **A:** Test datası ya da ön koşul olması zorunlu olmayan testler (5 kriter)
- **B:** Mutlaka ön koşul gerektiren testler (6 kriter)
- **C:** Mutlaka test datası gerektiren testler (6 kriter)
- **D:** Hem test datası hem ön koşul gerektiren testler (7 kriter)

**Kriterler:**
1. Test başlığı anlaşılır mı?
2. Öncelik bilgisi girilmiş mi?
3. Test datası eklenmiş mi? *(C, D için)*
4. Test ön koşul eklenmiş mi? *(B, D için)*
5. Test stepleri var ve doğru ayrıştırılmış mı?
6. Senaryonun hangi clientta koşulacağı belli mi?
7. Expected result bulunuyor mu?
""")

uploaded_file = st.file_uploader("📤 CSV dosyanızı yükleyin", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')
    st.success("✅ Dosya başarıyla yüklendi. Şimdi örnekleri puanlayalım.")

    sample_size = st.slider("📌 Kaç test case örneği değerlendirilsin?", min_value=1, max_value=len(df), value=5)
    sampled_df = df.sample(n=sample_size, random_state=42)

    def score_case(row):
        key = row['Issue key']
        summary = str(row['Summary']).strip()
        priority = str(row['Priority']).strip().lower()
        labels = str(row['Labels']).lower()
        steps_field = str(row['Custom field (Manual Test Steps)'])

        action_match = re.search(r'"Action"\s*:\s*"(.*?)"', steps_field)
        data_match = re.search(r'"Data"\s*:\s*"(.*?)"', steps_field)
        expected_match = re.search(r'"Expected Result"\s*:\s*"(.*?)"', steps_field)

        action = action_match.group(1) if action_match else ""
        data = data_match.group(1) if data_match else ""
        expected = expected_match.group(1) if expected_match else ""

        testdata_needed = bool(data.strip()) or bool(re.search(r'data:|msisdn|token|auth|account|payload|config', steps_field, re.IGNORECASE))
        precondition_needed = (
            'precond' in labels
            or bool(re.search(r'precond|\bön koşul\b|setup|required|gereklidir', steps_field, re.IGNORECASE))
        )

        if testdata_needed and precondition_needed:
            table = "D"
            base = 14
            aktif_kriterler = [1, 2, 3, 4, 5, 6, 7]
        elif testdata_needed:
            table = "C"
            base = 17
            aktif_kriterler = [1, 2, 3, 5, 6, 7]
        elif precondition_needed:
            table = "B"
            base = 17
            aktif_kriterler = [1, 2, 4, 5, 6, 7]
        else:
            table = "A"
            base = 20
            aktif_kriterler = [1, 2, 5, 6, 7]

        explanations = []
        total = 0
        kriter_puanlari = dict.fromkeys([
            "Başlık Puanı", "Öncelik Puanı", "Data Puanı", "Precondition Puanı", "Step Puanı", "Client Puanı", "Expected Puanı"
        ], None)

        if 1 in aktif_kriterler:
            if len(summary) < 10:
                explanations.append("❌ Test başlığı çok kısa, yeterli değil (0 puan)")
                kriter_puanlari["Başlık Puanı"] = 0
            elif any(word in summary.lower() for word in ["alanına gidilir", "tıklanır"]):
                explanations.append(f"🔸 Test başlığı zayıf ifade edilmiş: {summary} (puan: {base-3})")
                kriter_puanlari["Başlık Puanı"] = base - 3
                total += base - 3
            else:
                explanations.append("✅ Test başlığı anlaşılır (tam puan)")
                kriter_puanlari["Başlık Puanı"] = base
                total += base

        if 2 in aktif_kriterler:
            if priority in ["", "null", "none"]:
                explanations.append("❌ Öncelik bilgisi eksik")
                kriter_puanlari["Öncelik Puanı"] = 0
            else:
                explanations.append("✅ Öncelik bilgisi girilmiş")
                kriter_puanlari["Öncelik Puanı"] = base
                total += base

        if 3 in aktif_kriterler:
            if data.strip():
                explanations.append("✅ Test datası girilmiş")
                kriter_puanlari["Data Puanı"] = base
                total += base
            else:
                explanations.append("❌ Test datası eksik")
                kriter_puanlari["Data Puanı"] = 0

        if 4 in aktif_kriterler:
            if precondition_needed:
                explanations.append("✅ Ön koşul gerekli ve belirtilmiş")
                kriter_puanlari["Precondition Puanı"] = base
                total += base
            else:
                explanations.append("❌ Ön koşul gerekli ancak eksik")
                kriter_puanlari["Precondition Puanı"] = 0

        if 5 in aktif_kriterler:
            if not action.strip():
                explanations.append("❌ Step alanı tamamen boş")
                kriter_puanlari["Step Puanı"] = 0
            elif any(token in action for token in [",", " ve ", " ardından ", " sonra"]):
                explanations.append(f"🔸 Adımlar tek stepe yazılmış: {action} (puan: 3)")
                kriter_puanlari["Step Puanı"] = 3
                total += 3
            else:
                explanations.append("✅ Stepler doğru şekilde ayrılmış")
                kriter_puanlari["Step Puanı"] = base
                total += base

        if 6 in aktif_kriterler:
            client_keywords = ["android", "ios", "web", "mac", "windows"]
            if any(kw in summary.lower() for kw in client_keywords) or any(kw in action.lower() for kw in client_keywords):
                explanations.append("✅ Client bilgisi var")
                kriter_puanlari["Client Puanı"] = base
                total += base
            else:
                explanations.append("❌ Hangi clientta koşulacağı belirtilmemiş")
                kriter_puanlari["Client Puanı"] = 0

        if 7 in aktif_kriterler:
            if not expected.strip():
                explanations.append("❌ Expected result tamamen boş")
                kriter_puanlari["Expected Puanı"] = 0
            elif any(word in expected.lower() for word in ["test edilir", "kontrol edilir"]):
                explanations.append(f"🔸 Expected result zayıf ifade edilmiş: {expected} (puan: {base-3})")
                kriter_puanlari["Expected Puanı"] = base - 3
                total += base - 3
            else:
                explanations.append("✅ Expected result düzgün yazılmış")
                kriter_puanlari["Expected Puanı"] = base
                total += base

        return {
            "Key": key,
            "Summary": summary,
            "Tablo": table,
            "Action": action,
            "Data": data,
            "Expected": expected,
            **kriter_puanlari,
            "Toplam Puan": total,
            "Açıklama": "\n".join(explanations)
        }

    sonuçlar = sampled_df.apply(score_case, axis=1, result_type='expand')

    st.markdown("## 📊 Değerlendirme Sonuçları")
    st.dataframe(sonuçlar)

    csv = sonuçlar.to_csv(index=False, sep=';', encoding='utf-8')
    st.download_button("📥 Sonuçları indir (CSV)", data=csv, file_name="testcase_skorlari.csv", mime="text/csv")

    st.markdown("## 📝 Detaylı Açıklamalar")
    for _, row in sonuçlar.iterrows():
        st.markdown(f"### 🔍 {row['Key']} — {row['Summary']}")
        st.markdown(f"**Tablo:** `{row['Tablo']}`  |  **Puan:** `{row['Toplam Puan']}`")
        st.info(row['Açıklama'])


# -*- coding: utf-8 -*-
# 📌 Test Case Evaluator v1.6 – UI sade (debug & "neden bu tablo" kaldırıldı)
import streamlit as st
import pandas as pd
import re
import time
import random

st.set_page_config(page_title="Test Case SLA", layout="wide")
st.title("📋 Test Case Kalite Değerlendirmesi")

st.markdown("""
Bu uygulama test caseleri **A/B/C/D** tablosuna göre **senaryo içeriğini analiz ederek** otomatik sınıflandırır ve 7 kritere göre puanlar.
- **Tablo seçimi:** Gerçekten **data/önkoşul gereksinimi** var mı diye içerik sinyallerine bakılır.
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

""")

col1, col2 = st.columns([1,1])
sample_size = col1.slider("📌 Kaç test case değerlendirilsin?", 1, 100, 5)
fix_seed = col2.toggle("🔒 Fix seed (deterministik örnekleme)", value=False)

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
    if _match(r'\b(select|insert|update|delete)\b', t): signals.append("SQL")
    if _match(r'\b(json|payload|body|request|response|headers|content-type)\b', t) and _match(r'"\w+"\s*:\s*".+?"', t): signals.append("JSON body")
    if _match(r'\b(msisdn|token|iban|imei|email|username|password|user[_\-]?id|subscriber)\b', t): signals.append("Kimlik alanı")
    if _match(r'\b(post|put|patch)\b', t) and _match(r'\b(body|payload)\b', t): signals.append("POST payload")
    if _match(r'<\s*(msisdn|token|iban|imei|email|username|password|user[_\-]?id)\s*>', t) or \
       _match(r'\{\s*(msisdn|token|iban|imei|email|username|password|user[_\-]?id)\s*\}', t): signals.append("Placeholder(ID)")
    return signals

def scan_precond_signals(text:str):
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
    - Aksi halde, güçlü sinyal sayısı ≥ 2 ise GEREKLİ.
    """
    combined = (summary or "") + "\n" + (steps_text or "")
    data_field = extract_first(steps_text, "Data")
    data_tag = has_data_tag(steps_text)
    signals = scan_data_signals(combined)

    if data_tag or (data_field.strip() != ""):
        return True
    return len(set(signals)) >= 2

def decide_precond_needed(summary:str, steps_text:str):
    combined = (summary or "") + "\n" + (steps_text or "")
    signals = scan_precond_signals(combined)
    return len(set(signals)) >= 1

def choose_table(summary, steps_text):
    """Tablo seçimi (eşikli, false-positive azaltılmış)."""
    data_needed = decide_data_needed(summary, steps_text)
    pre_needed = decide_precond_needed(summary, steps_text)

    if data_needed and pre_needed:
        return "D", 14, [1,2,3,4,5,6,7]
    if data_needed:
        return "C", 17, [1,2,3,5,6,7]
    if pre_needed:
        return "B", 17, [1,2,4,5,6,7]
    return "A", 20, [1,2,5,6,7]

def score_one(row):
    key = _text(row.get('Issue key') or row.get('Issue Key'))
    summary = _text(row.get('Summary'))
    priority = _text(row.get('Priority')).lower()
    steps_text = _text(row.get('Custom field (Manual Test Steps)'))

    action = extract_first(steps_text, "Action")
    expected = extract_first(steps_text, "Expected Result")

    table, base, active = choose_table(summary, steps_text)

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
        if decide_precond_needed(summary, steps_text):
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

    return {
        "Key": key,
        "Summary": summary,
        "Tablo": table,
        "Toplam Puan": total,
        **pts,
        "Açıklama": " | ".join(notes),
    }

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
        for k in ['Başlık','Öncelik','Data','Ön Koşul','Stepler','Client','Expected']:
            if k in r and pd.notna(r[k]):
                st.markdown(f"- **{k}**: {int(r[k])} puan")
        st.markdown(f"🗒️ **Açıklamalar:** {r['Açıklama']}")
