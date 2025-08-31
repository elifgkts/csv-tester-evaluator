# -*- coding: utf-8 -*-
# 📌 Test Case Evaluator v2.6
# - Dark mode CSS
# - Data/Precondition: gerçek içerik kontrolü (HTML/JSON/blok başlıkları)
# - Expected Result: TÜM adımlar taranır; herhangi birinde varsa puan
# - Stepler (GÜNCEL KURAL): Tek Action bloğu + çok adım VEYA edilgen ifade → 1 puan
# - KPI, tablo, CSV ve Detay Kartları + debug

import streamlit as st
import pandas as pd
import re
import time
import random
from datetime import datetime

# ---------- Sayfa & Stil ----------
st.set_page_config(page_title="Test Case SLA", layout="wide")

CUSTOM_CSS = """
<style>
:root{
  --bg-card:#ffffff;
  --text-strong:#0f172a;
  --text-soft:#475569;
  --text-sub:#64748b;
  --border:rgba(2,6,23,0.08);

  --badge-a-bg:#eef2ff; --badge-a-fg:#3730a3; --badge-a-bd:#c7d2fe;
  --badge-b-bg:#ecfeff; --badge-b-fg:#155e75; --badge-b-bd:#a5f3fc;
  --badge-c-bg:#fef9c3; --badge-c-fg:#854d0e; --badge-c-bd:#fde68a;
  --badge-d-bg:#fee2e2; --badge-d-fg:#991b1b; --badge-d-bd:#fecaca;
}
@media (prefers-color-scheme: dark){
  :root{
    --bg-card:#0b1220;
    --text-strong:#e5ecff;
    --text-soft:#c7d2fe;
    --text-sub:#94a3b8;
    --border:rgba(148,163,184,0.25);

    --badge-a-bg:#1e1b4b; --badge-a-fg:#c7d2fe; --badge-a-bd:#3730a3;
    --badge-b-bg:#083344; --badge-b-fg:#99f6e4; --badge-b-bd:#155e75;
    --badge-c-bg:#3f3f1e; --badge-c-fg:#fde68a; --badge-c-bd:#854d0e;
    --badge-d-bg:#431313; --badge-d-fg:#fecaca; --badge-d-bd:#991b1b;
  }
}
#MainMenu, footer {visibility:hidden;}
.app-hero{
  background: linear-gradient(135deg, #1f6feb 0%, #0ea5e9 100%);
  color:#fff; padding:18px 22px; border-radius:14px; margin-bottom:18px;
  box-shadow:0 8px 24px rgba(2, 6, 23, 0.18);
}
.app-hero h1{ font-size:24px; margin:0 0 6px 0; line-height:1.2; color:#fff; }
.app-hero p{ margin:0; opacity:.95; color:#fff; }
.kpi{
  border-radius:14px; padding:14px; background:var(--bg-card);
  border:1px solid var(--border); box-shadow:0 4px 16px rgba(2,6,23,0.06);
}
.kpi .kpi-title{ font-size:12px; color:var(--text-sub); margin-bottom:6px; }
.kpi .kpi-value{ font-size:20px; font-weight:700; color:var(--text-strong); }
.kpi .kpi-sub{ font-size:12px; color:var(--text-sub); }

.badge{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px;
  border:1px solid var(--border); background:#f8fafc; color:var(--text-strong); }
.badge-a{ background:var(--badge-a-bg); color:var(--badge-a-fg); border-color:var(--badge-a-bd);}
.badge-b{ background:var(--badge-b-bg); color:var(--badge-b-fg); border-color:var(--badge-b-bd);}
.badge-c{ background:var(--badge-c-bg); color:var(--badge-c-fg); border-color:var(--badge-c-bd);}
.badge-d{ background:var(--badge-d-bg); color:var(--badge-d-fg); border-color:var(--badge-d-bd);}

.case-card{
  border-radius:14px; padding:14px 16px; background:var(--bg-card);
  border:1px solid var(--border); box-shadow:0 6px 24px rgba(2,6,23,0.06);
  margin-bottom:14px;
}
.case-head{ display:flex; align-items:center; justify-content:space-between; gap:8px;
  border-bottom:1px dashed var(--border); padding-bottom:8px; margin-bottom:8px; }
.case-title{ font-weight:700; color:var(--text-strong); }
.case-meta{ font-size:12px; color:var(--text-soft); }
.hr-soft{ border:none; border-top:1px dashed var(--border); margin:8px 0; }

h1,h2,h3,h4,h5,h6, .stMarkdown p, .stMarkdown li{ color:var(--text-strong) !important; }
small, .help, .hint{ color:var(--text-sub) !important; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(f"""
<div class="app-hero">
  <h1>📋 Test Case Kalite Değerlendirmesi</h1>
  <p>Test caseleri A/B/C/D tablosuna göre senaryo içeriğini analiz ederek puanlar.
  <span style="opacity:0.8">Rapor zamanı: {datetime.now().strftime('%d.%m.%Y %H:%M')}</span></p>
</div>
""", unsafe_allow_html=True)

with st.expander("📌 Kurallar (özet)"):
    st.markdown("""
- **CSV ayraç:** `;`  
- **Gerekli sütunlar:** `Issue key` (veya `Issue Key`), `Summary`, `Priority`, `Labels`, `Custom field (Manual Test Steps)`  
- **Tablo mantığı (senaryoya göre):** A: Data/Pre yok • B: Pre gerekli • C: Data gerekli • D: Data+Pre gerekli  
- **Puanlar:** A=5×20, B=6×17, C=6×17, D=7×14
""")

# ---------- Sidebar ----------
st.sidebar.header("⚙️ Ayarlar")
sample_size = st.sidebar.slider("Kaç test case değerlendirilsin?", 1, 100, 5)
fix_seed = st.sidebar.toggle("🔒 Fix seed (deterministik örnekleme)", value=False)
show_debug = st.sidebar.toggle("🛠 Debug (Data/Action/Expected)", value=False)
if "reroll" not in st.session_state: st.session_state.reroll = 0
if st.sidebar.button("🎲 Yeniden örnekle"): st.session_state.reroll += 1

uploaded = st.file_uploader("📤 CSV yükle (`;` ayraçlı)", type="csv")

# ---------- Yardımcılar ----------
def _text(x):
    return str(x or "")

def _match(pattern, text):
    return re.search(pattern, text or "", re.IGNORECASE)

def _cleanup_html(s: str) -> str:
    s = s or ""
    s = re.sub(r'<br\s*/?>', '\n', s, flags=re.I)
    s = re.sub(r'</?(p|div|li|tr|td|th|ul|ol|span)>', '\n', s, flags=re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    return s

def _is_meaningless(val: str) -> bool:
    meaningless = {"", "-", "—", "none", "n/a", "na", "null", "yok"}
    return re.sub(r'\s+', ' ', (val or '')).strip().lower() in meaningless

def extract_first(text, key):
    m = re.search(rf'"{key}"\s*:\s*"(.*?)"', text or "", re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""

# ---- DATA ALGILAMA (blok + JSON + HTML) ----
def extract_data_blocks(steps_text: str) -> list[str]:
    blocks = []
    # JSON "Data":"..."
    for m in re.finditer(r'"Data"\s*:\s*"(?:\\.|[^"])*"', steps_text or "", re.IGNORECASE | re.DOTALL):
        raw = m.group(0)
        val = re.sub(r'^.*?":\s*"(.*)"$', r'\1', raw, flags=re.DOTALL)
        val = val.replace('\\"', '"').strip()
        if val:
            blocks.append(val)
    # HTML/metin: Data başlığından bir sonraki başlığa
    txt = _cleanup_html(steps_text)
    pattern = re.compile(
        r'(?:^|\n)\s*Data\s*:?\s*(.*?)\s*(?=(?:^|\n)\s*(?:Expected\s*Result|Action|Attachments?)\b|$)',
        re.IGNORECASE | re.DOTALL
    )
    for m in pattern.finditer(txt):
        val = m.group(1).strip()
        if val:
            blocks.append(val)
    return [b for b in blocks if b.strip()]

def is_meaningful_data(value: str) -> bool:
    if _is_meaningless(value):
        return False
    v = value.strip()
    if re.search(r'https?://', v, re.I): return True
    if re.search(r'\b(select|insert|update|delete)\b', v, re.I): return True
    if re.search(r'\b[a-z_]+\.[a-z_]+\b', v, re.I): return True  # tablo.adı
    if len(re.sub(r'\s+', '', v)) >= 2: return True
    return False

def has_data_present_for_scoring(steps_text: str) -> bool:
    blocks = extract_data_blocks(steps_text)
    return any(is_meaningful_data(b) for b in blocks)

# ---- PRECONDITION (var mı? & sinyal) ----
def has_precond_tag_with_value(steps_text: str) -> bool:
    pattern = re.compile(r'(?:^|\r?\n)\s*[-\s]*Precondition\s*:\s*(.*)', re.IGNORECASE)
    for m in pattern.finditer(steps_text or ""):
        val = (m.group(1) or "").strip()
        if not _is_meaningless(val): return True
    # JSON
    for m in re.finditer(r'"Precondition"\s*:\s*"(.*?)"', steps_text or "", re.IGNORECASE | re.DOTALL):
        val = (m.group(1) or "").strip()
        if not _is_meaningless(val): return True
    return False

def scan_data_signals(text: str):
    t = (text or "").lower()
    signals = []
    if _match(r'\b(select|insert|update|delete)\b', t): signals.append("SQL")
    if _match(r'\b(json|payload|body|request|response|headers|content-type)\b', t) and _match(r'"\w+"\s*:\s*".+?"', t):
        signals.append("JSON body")
    if _match(r'\b(msisdn|token|iban|imei|email|username|password|user[_\\-]?id|subscriber)\b', t): signals.append("ID field")
    if _match(r'\b(post|put|patch)\b', t) and _match(r'\b(body|payload)\b', t): signals.append("POST payload")
    if _match(r'<\\s*(msisdn|token|iban|imei|email|username|password|user[_\\-]?id)\\s*>', t) or \
       _match(r'\\{\\s*(msisdn|token|iban|imei|email|username|password|user[_\\-]?id)\\s*\\}', t):
        signals.append("Placeholder(ID)")
    return list(set(signals))

def scan_precond_signals(text: str):
    t = (text or "").lower()
    signals = []
    if _match(r'\bprecondition\b|ön\s*koşul|given .*already', t): signals.append("Precondition ifadesi")
    if _match(r'\b(logged in|login|giriş yap(mış|ın)|authenticated|auth)\b', t): signals.append("Login/Auth")
    if _match(r'\b(subscription|abonelik)\b.*\b(aktif|var|existing)\b', t): signals.append("Abonelik aktif")
    if _match(r'\bexisting user|mevcut kullanıcı\b', t): signals.append("Mevcut kullanıcı/hesap")
    if _match(r'\b(seed|setup|config(ure|)|feature flag|whitelist|allowlist|role|permission)\b', t): signals.append("Ortam/Ayar/Yetki")
    return list(set(signals))

def decide_data_needed(summary: str, steps_text: str) -> bool:
    if has_data_present_for_scoring(steps_text):
        return True
    combined = (summary or "") + "\n" + (steps_text or "")
    return len(scan_data_signals(combined)) >= 2  # en az iki güçlü sinyal → data gerekli

def decide_precond_needed(summary: str, steps_text: str) -> bool:
    if has_precond_tag_with_value(steps_text):
        return True
    combined = (summary or "") + "\n" + (steps_text or "")
    return len(scan_precond_signals(combined)) >= 1

def choose_table(summary: str, steps_text: str):
    data_needed = decide_data_needed(summary, steps_text)
    pre_needed = decide_precond_needed(summary, steps_text)
    if data_needed and pre_needed: return "D", 14, [1,2,3,4,5,6,7]
    if data_needed: return "C", 17, [1,2,3,5,6,7]
    if pre_needed: return "B", 17, [1,2,4,5,6,7]
    return "A", 20, [1,2,5,6,7]

# ---- ACTION/STEPLER ----
def extract_action_blocks(steps_text: str) -> list[str]:
    blocks = []
    # JSON "Action":"..."
    for m in re.finditer(r'"Action"\s*:\s*"(?:\\.|[^"])*"', steps_text or "", re.IGNORECASE | re.DOTALL):
        raw = m.group(0)
        val = re.sub(r'^.*?":\s*"(.*)"$', r'\1', raw, flags=re.DOTALL)
        val = val.replace('\\"', '"').strip()
        if val:
            blocks.append(val)
    # HTML/metin: Action başlığından bir sonraki başlığa
    txt = _cleanup_html(steps_text)
    pattern = re.compile(
        r'(?:^|\n)\s*Action\s*:?\s*(.*?)\s*(?=(?:^|\n)\s*(?:Data|Expected\s*Result|Attachments?)\b|$)',
        re.IGNORECASE | re.DOTALL
    )
    for m in pattern.finditer(txt):
        val = m.group(1).strip()
        if val:
            blocks.append(val)
    return [b for b in blocks if b.strip()]

def block_has_many_substeps(text: str) -> bool:
    """Tek Action bloğu içinde çok adım yazılmış mı?"""
    t = _cleanup_html(text or "")
    if re.search(r'(^|\n)\s*(\d+[\).\-\:]|\-|\*|\•)\s+\S+', t): return True  # numbered/bulleted
    lines = [ln.strip() for ln in re.split(r'(?:\r?\n)+', t) if ln.strip()]
    if len(lines) >= 3: return True
    if t.count(';') >= 2: return True
    joiners = re.findall(r'(?:,|\bve\b|\bsonra\b|\bardından\b)', t, re.I)
    if len(joiners) >= 3: return True
    return False

# ---- EXPECTED ----
def extract_expected_blocks(steps_text: str) -> list[str]:
    blocks = []
    for m in re.finditer(r'"Expected\s*Result"\s*:\s*"(?:\\.|[^"])*"', steps_text or "", re.IGNORECASE | re.DOTALL):
        raw = m.group(0)
        val = re.sub(r'^.*?":\s*"(.*)"$', r'\1', raw, flags=re.DOTALL)
        val = val.replace('\\"', '"').strip()
        if val:
            blocks.append(val)
    txt = _cleanup_html(steps_text)
    pattern = re.compile(
        r'(?:^|\n)\s*Expected\s*Result\s*:?\s*(.*?)\s*(?=(?:^|\n)\s*(?:Action|Data|Attachments?)\b|$)',
        re.IGNORECASE | re.DOTALL
    )
    for m in pattern.finditer(txt):
        val = m.group(1).strip()
        if val:
            blocks.append(val)
    return [b for b in blocks if b.strip()]

def is_meaningful_expected(value: str) -> bool:
    if _is_meaningless(value):
        return False
    v = value.strip()
    return len(re.sub(r'\s+', '', v)) >= 2

def has_expected_present(steps_text: str) -> bool:
    blocks = extract_expected_blocks(steps_text)
    return any(is_meaningful_expected(b) for b in blocks)

# ---------- Skorlama ----------
PASSIVE_PATTERNS = re.compile(r'\b(yapıldı|edildi|gerçekleştirildi|sağlandı|tamamlandı|kontrol edildi)\b', re.I)

def score_one(row):
    key = _text(row.get('Issue key') or row.get('Issue Key') or row.get('Key') or row.get('IssueKey'))
    summary = _text(row.get('Summary') or row.get('Issue Summary') or row.get('Title'))
    priority = _text(row.get('Priority')).lower()
    # steps sütun adını bul
    steps_col_name = None
    for cand in ['Custom field (Manual Test Steps)', 'Manual Test Steps', 'Steps', 'Custom Steps']:
        if cand in row.index:
            steps_col_name = cand
            break
    steps_text = _text(row.get(steps_col_name)) if steps_col_name else ""

    action_blocks = extract_action_blocks(steps_text)
    all_actions_text = " \n ".join(action_blocks)
    expected_present = has_expected_present(steps_text)

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

    # 3) Data
    if 3 in active:
        if has_data_present_for_scoring(steps_text):
            pts['Data'] = base; notes.append("✅ Data mevcut"); total += base
        else:
            pts['Data'] = 0; notes.append("❌ Data bulunamadı")

    # 4) Ön Koşul
    if 4 in active:
        if has_precond_tag_with_value(steps_text) or decide_precond_needed(summary, steps_text):
            pts['Ön Koşul'] = base; notes.append("✅ Ön koşul belirtilmiş/ima edilmiş"); total += base
        else:
            pts['Ön Koşul'] = 0; notes.append("❌ Ön koşul eksik")

    # 5) Stepler — GÜNCEL KURAL
    if 5 in active:
        n_blocks = len(action_blocks)
        if n_blocks == 0:
            pts['Stepler'] = 0; notes.append("❌ Stepler boş")
        elif n_blocks >= 2:
            pts['Stepler'] = base; notes.append(f"✅ Stepler ayrı ve düzgün ({n_blocks} adım)"); total += base
        else:
            # n_blocks == 1
            t = (action_blocks[0] or "")
            if block_has_many_substeps(t) or PASSIVE_PATTERNS.search(t):
                pts['Stepler'] = 1
                notes.append("❌ Tek blokta çok adım veya edilgen ifade (1 puan)")
                total += 1
            else:
                pts['Stepler'] = base; notes.append("✅ Tek step ama net/tek eylem"); total += base

    # 6) Client
    if 6 in active:
        ck = ["android","ios","web","mac","windows","chrome","safari"]
        if any(c in (summary or "").lower() for c in ck) or any(c in (all_actions_text or "").lower() for c in ck):
            pts['Client'] = base; notes.append("✅ Client bilgisi var"); total += base
        else:
            pts['Client'] = 0; notes.append("❌ Client bilgisi eksik")

    # 7) Expected (HERHANGİ bir adımda varsa puan)
    if 7 in active:
        if expected_present:
            pts['Expected'] = base; notes.append("✅ Expected mevcut (adımlardan en az birinde)")
            total += base
        else:
            pts['Expected'] = 0; notes.append("❌ Expected result eksik")

    return {
        "Key": key, "Summary": summary, "Tablo": table, "Toplam Puan": total,
        **pts, "Açıklama": " | ".join(notes),
        "_raw_steps": steps_text, "_actions": action_blocks  # debug amaçlı
    }

# ---------- Çalıştır ----------
if uploaded:
    if fix_seed:
        random.seed(20250831 + st.session_state.reroll)
    else:
        random.seed(time.time_ns())

    try:
        df = pd.read_csv(uploaded, sep=';')
    except Exception:
        df = pd.read_csv(uploaded)

    sample = df.sample(n=min(sample_size, len(df)),
                       random_state=(123 if fix_seed else None)) if len(df)>0 else df

    results = sample.apply(score_one, axis=1, result_type='expand')

    # KPI Özetleri
    total_cases = len(results)
    avg_score = round(results["Toplam Puan"].mean() if total_cases else 0, 1)
    min_score = int(results["Toplam Puan"].min()) if total_cases else 0
    max_score = int(results["Toplam Puan"].max()) if total_cases else 0
    dist = results['Tablo'].value_counts().reindex(["A","B","C","D"]).fillna(0).astype(int)

    k1, k2, k3, k4 = st.columns([1,1,1,1])
    with k1:
        st.markdown('<div class="kpi"><div class="kpi-title">Toplam Örnek</div><div class="kpi-value">{}</div><div class="kpi-sub">Değerlendirilen</div></div>'.format(total_cases), unsafe_allow_html=True)
    with k2:
        st.markdown('<div class="kpi"><div class="kpi-title">Dağılım (A/B/C/D)</div><div class="kpi-value">{}/{}/{}/{}</div><div class="kpi-sub">Tablo adetleri</div></div>'.format(dist["A"],dist["B"],dist["C"],dist["D"]), unsafe_allow_html=True)
    with k3:
        st.markdown('<div class="kpi"><div class="kpi-title">Ortalama Skor</div><div class="kpi-value">{}</div><div class="kpi-sub">Min: {} • Max: {}</div></div>'.format(avg_score, min_score, max_score), unsafe_allow_html=True)
    with k4:
        st.markdown('<div class="kpi"><div class="kpi-title">Rapor Zamanı</div><div class="kpi-value">{}</div><div class="kpi-sub">Yerel saat</div></div>'.format(datetime.now().strftime("%H:%M")), unsafe_allow_html=True)

    st.markdown("### 📈 Tablo Dağılımı")
    st.bar_chart(dist)

    # Skor tablosu + CSV
    MAX_BY_TABLE = {"A": 100, "B": 102, "C": 102, "D": 98}
    results["Maks Puan"] = results["Tablo"].map(MAX_BY_TABLE).fillna(100)
    results["Skor %"] = (results["Toplam Puan"] / results["Maks Puan"]).clip(0,1) * 100
    results["Skor %"] = results["Skor %"].round(1)

    show_df = results[["Key","Summary","Tablo","Toplam Puan","Skor %","Açıklama"]].copy()
    st.markdown("## 📊 Değerlendirme Tablosu")
    st.dataframe(
        show_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Key": st.column_config.TextColumn("Key", help="Issue key"),
            "Summary": st.column_config.TextColumn("Summary", width="medium"),
            "Tablo": st.column_config.TextColumn("Tablo"),
            "Toplam Puan": st.column_config.NumberColumn("Toplam Puan", format="%d"),
            "Skor %": st.column_config.ProgressColumn("Skor %", help="Toplam puanın tabloya göre maksimuma oranı", min_value=0, max_value=100),
            "Açıklama": st.column_config.TextColumn("Açıklama", width="large"),
        }
    )

    st.download_button(
        "📥 Sonuçları CSV olarak indir",
        data=show_df.to_csv(index=False, sep=';', encoding='utf-8'),
        file_name=f"testcase_skorlari_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )

    # ---------- Detay Kartları ----------
    st.markdown("## 📝 Detaylar")
    badge_map = {"A":"badge badge-a","B":"badge badge-b","C":"badge badge-c","D":"badge badge-d"}

    for idx, r in results.iterrows():
        max_pt = MAX_BY_TABLE.get(r["Tablo"], 100)
        pct = float(r["Toplam Puan"]) / max_pt if max_pt else 0
        badge_class = badge_map.get(r["Tablo"], "badge")

        st.markdown('<div class="case-card">', unsafe_allow_html=True)
        st.markdown(f'''
            <div class="case-head">
              <div class="case-title">🔍 {r["Key"]} — {r["Summary"]}</div>
              <div class="case-meta"><span class="{badge_class}">Tablo {r["Tablo"]}</span></div>
            </div>
        ''', unsafe_allow_html=True)

        c1, c2 = st.columns([3,1])
        with c1:
            st.markdown(f"**Toplam Puan:** `{int(r['Toplam Puan'])}` / `{int(max_pt)}`")
            st.progress(min(max(pct,0),1.0))
        with c2:
            st.markdown(f"**Skor %:** **{round(pct*100,1)}%**")

        st.markdown("<hr class='hr-soft'/>", unsafe_allow_html=True)

        kriterler = ['Başlık','Öncelik','Data','Ön Koşul','Stepler','Client','Expected']
        for k in kriterler:
            if k in r and pd.notna(r[k]):
                st.markdown(f"- **{k}**: {int(r[k])} puan")

        if show_debug:
            from html import escape
            data_blocks = extract_data_blocks(r["_raw_steps"])
            exp_blocks = extract_expected_blocks(r["_raw_steps"])
            act_blocks = r["_actions"] or []
            st.markdown(f"<small><strong>Action blok sayısı:</strong> {len(act_blocks)}</small>", unsafe_allow_html=True)
            st.markdown(f"<small><strong>Birleşik Action? </strong> {block_has_many_substeps(act_blocks[0]) if len(act_blocks)==1 else False}</small>", unsafe_allow_html=True)
            st.markdown(f"<small><strong>Data Blokları:</strong> {' | '.join(escape(b) for b in data_blocks) or '—'}</small>", unsafe_allow_html=True)
            st.markdown(f"<small><strong>Expected Blokları:</strong> {' | '.join(escape(b) for b in exp_blocks) or '—'}</small>", unsafe_allow_html=True)

        st.markdown(f"🗒️ **Açıklamalar:** {r['Açıklama']}")
        st.markdown('</div>', unsafe_allow_html=True)
