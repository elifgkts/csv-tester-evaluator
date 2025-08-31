# -*- coding: utf-8 -*-
# 📌 Test Case Evaluator v1.7 – PDF çıktısı (ReportLab) + aynı sade UI
import streamlit as st
import pandas as pd
import re
import time
import random
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Test Case SLA", layout="wide")
st.title("📋 Test Case Kalite Değerlendirmesi")

st.markdown("""
Bu uygulama test caseleri **A/B/C/D** tablosuna göre **senaryo içeriğini analiz ederek** otomatik sınıflandırır ve 7 kritere göre puanlar.
- **Data puanı:** Sadece *Manual Test Steps* içinde **`Data:`** etiketi varsa verilir.
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

col1, col2 = st.columns([1,1])
sample_size = col1.slider("📌 Kaç test case değerlendirilsin?", 1, 100, 5)
fix_seed = col2.toggle("🔒 Fix seed (deterministik örnekleme)", value=False)

# İsteğe bağlı PDF fontu (Türkçe karakterler için önerilir)
with st.expander("🅰️ PDF için özel font yükle (opsiyonel)"):
    font_file = st.file_uploader("Bir .ttf font dosyası yükleyin (öneri: DejaVuSans.ttf)", type=["ttf"])

if "reroll" not in st.session_state:
    st.session_state.reroll += 0
if st.button("🎲 Yeniden örnekle"):
    st.session_state.reroll += 1

uploaded = st.file_uploader("📤 CSV yükle (`;` ayraçlı)", type="csv")

# ---------- Yardımcılar ----------
def _text(x): 
    return str(x or "")

def _match(pattern, text):
    return re.search(pattern, text or "", re.IGNORECASE)

def has_data_tag(steps_text:str) -> bool:
    return bool(re.search(r'(?:^|\n|\r)\s*[-\s]*Data\s*:', steps_text or "", re.IGNORECASE))

def extract_first(text, key):
    m = re.search(rf'"{key}"\s*:\s*"(.*?)"', text or "", re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""

def scan_data_signals(text:str):
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

    return pts, " | ".join(notes), total

# ---------- Çalıştır ----------
if uploaded:
    # seed yönetimi (deterministik istenirse)
    if fix_seed:
        random.seed(20250831 + st.session_state.reroll)
    else:
        random.seed(time.time_ns())

    # CSV oku
    try:
        df = pd.read_csv(uploaded, sep=';')
    except Exception:
        df = pd.read_csv(uploaded)

    # Örnekleme
    if len(df) > sample_size:
        idx = random.sample(range(len(df)), sample_size)
        sample = df.iloc[idx].copy()
    else:
        sample = df.copy()

    # Hesapla
    rows = []
    for _, row in sample.iterrows():
        key = _text(row.get('Issue key') or row.get('Issue Key'))
        summary = _text(row.get('Summary'))
        pts, notes, total = score_one(row)
        table = choose_table(summary, _text(row.get('Custom field (Manual Test Steps)')))[0]
        rows.append({
            "Key": key,
            "Summary": summary,
            "Tablo": table,
            "Toplam Puan": total,
            **pts,
            "Açıklama": notes
        })
    results = pd.DataFrame(rows)

    # Dağılım
    st.markdown("### 📈 Tablo Dağılımı")
    dist = results['Tablo'].value_counts().sort_index()
    st.write({k:int(v) for k,v in dist.items()})

    # Tablo
    st.markdown("## 📊 Değerlendirme Tablosu")
    st.dataframe(results.set_index("Key"))

    # --------- PDF oluşturma ---------
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    except Exception as e:
        st.warning("PDF oluşturmak için lütfen şu komutla ReportLab kurun: `pip install reportlab`")
        st.stop()

    # Font ayarı (opsiyonel .ttf)
    body_font = "Helvetica"
    if font_file is not None:
        try:
            pdfmetrics.registerFont(TTFont("CustomFont", font_file.read()))
            body_font = "CustomFont"
        except Exception:
            st.info("⚠️ Font kaydedilemedi, Helvetica ile devam ediliyor.")

    # PDF içeriği
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="H1", fontName=body_font, fontSize=18, leading=22, spaceAfter=8))
    styles.add(ParagraphStyle(name="H2", fontName=body_font, fontSize=14, leading=18, spaceAfter=6))
    styles.add(ParagraphStyle(name="P", fontName=body_font, fontSize=10, leading=14))
    styles.add(ParagraphStyle(name="SMALL", fontName=body_font, fontSize=9, leading=12))

    story = []

    # Kapak
    story.append(Paragraph("📋 Test Case Kalite Değerlendirmesi", styles["H1"]))
    date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    story.append(Paragraph(f"Tarih: {date_str}", styles["SMALL"]))
    story.append(Spacer(1, 6))

    # Dağılım özeti
    story.append(Paragraph("📈 Tablo Dağılımı", styles["H2"]))
    dist_items = [[Paragraph(k, styles["P"]), Paragraph(str(v), styles["P"])] for k, v in dist.items()]
    dist_tbl = Table([["Tablo", "Adet"]] + dist_items, colWidths=[25*mm, 25*mm])
    dist_tbl.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,-1), body_font),
        ("ALIGN", (1,1), (-1,-1), "RIGHT"),
    ]))
    story.append(dist_tbl)
    story.append(Spacer(1, 10))

    # Skor tablosu (özet)
    story.append(Paragraph("📊 Değerlendirme Özeti", styles["H2"]))
    show_cols = ["Key", "Summary", "Tablo", "Toplam Puan"]
    # Summary metnini kırpmak için
    def _short(s, n=90):
        s = _text(s)
        return s if len(s) <= n else s[:n-1] + "…"
    table_data = [show_cols] + [[
        _text(r["Key"]),
        _short(r["Summary"]),
        _text(r["Tablo"]),
        str(int(r["Toplam Puan"])) if pd.notna(r["Toplam Puan"]) else ""
    ] for _, r in results.iterrows()]
    widths = [28*mm, 100*mm, 18*mm, 22*mm]
    t = Table(table_data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,-1), body_font),
        ("ALIGN", (-1,1), (-1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # Ayrıntılar (her test)
    for i, r in results.iterrows():
        story.append(Paragraph(f"🔍 {r['Key']} – {r['Summary']}", styles["H2"]))
        story.append(Paragraph(f"Tablo: <b>{r['Tablo']}</b> &nbsp;&nbsp; Toplam Puan: <b>{int(r['Toplam Puan']) if pd.notna(r['Toplam Puan']) else 0}</b>", styles["P"]))
        # Kriter tablosu
        kriterler = ['Başlık','Öncelik','Data','Ön Koşul','Stepler','Client','Expected']
        k_rows = [["Kriter", "Puan"]] + [[k, str(int(r[k])) if k in r and pd.notna(r[k]) else ""] for k in kriterler]
        kt = Table(k_rows, colWidths=[50*mm, 20*mm])
        kt.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.3, colors.grey),
            ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
            ("FONTNAME", (0,0), (-1,-1), body_font),
            ("ALIGN", (1,1), (1,-1), "RIGHT"),
        ]))
        story.append(kt)
        story.append(Spacer(1, 4))
        # Açıklama
        story.append(Paragraph("🗒️ Açıklamalar:", styles["P"]))
        story.append(Paragraph(_text(r["Açıklama"]), styles["SMALL"]))
        # Sayfa dolduysa otomatik bölünsün
        story.append(Spacer(1, 8))

        # Ara ara sayfa kır
        if (i+1) % 4 == 0:
            story.append(PageBreak())

    doc.build(story)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    st.download_button(
        "📄 PDF indir",
        data=pdf_bytes,
        file_name=f"testcase_degerlendirme_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
        mime="application/pdf"
    )

    # (İstersen kalsın diye CSV butonunu da gösterebilirim; dilersen kaldırabiliriz.)
    # st.download_button(
    #     "📥 CSV indir",
    #     data=results.to_csv(index=False, sep=';', encoding='utf-8'),
    #     file_name="testcase_skorlari.csv",
    #     mime="text/csv"
    # )
