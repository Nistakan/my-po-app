import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="PO to S-018 Generator", layout="wide")

if 'po_bucket' not in st.session_state:
    st.session_state.po_bucket = []

# --- HELPER FUNCTIONS ---
def load_master_data(file):
    if file is not None:
        return pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
    return None

def normalize_unit_logic(po_qty, price_unit_ratio, box_unit_ratio):
    try:
        po_qty, p_ratio, b_ratio = float(po_qty), float(price_unit_ratio), float(box_unit_ratio)
        return (po_qty * p_ratio) / b_ratio if b_ratio != 0 else 0
    except: return 0

# --- MAIN APP ---
st.title("📦 PO to Sales Order (S-018) Generator")
st.markdown("---")

# 1. SIDEBAR
with st.sidebar:
    st.header("⚙️ Master Data Management")
    uploaded_cus = st.file_uploader("Upload Cus_SaleList", type=['xlsx', 'csv'])
    uploaded_pd = st.file_uploader("Upload PD_pack", type=['xlsx', 'csv'])
    if st.button("Clear All POs in Bucket"):
        st.session_state.po_bucket = []
        st.rerun()

df_cus = load_master_data(uploaded_cus)
df_pd = load_master_data(uploaded_pd)

# 2. STEP 1: Selection & Display Logic (ปรับปรุงข้อ 2)
st.header("Step 1: Customer Selection")

if df_cus is not None:
    search_term = st.text_input("🔍 ค้นหาลูกค้า (รหัส หรือ ชื่อ)").strip().lower()
    mask = df_cus['รหัสลูกค้า'].str.lower().str.contains(search_term, na=False) | \
           df_cus['ชื่อลูกค้า'].str.lower().str.contains(search_term, na=False)
    filtered_cus = df_cus[mask]

    if not filtered_cus.empty:
        selected_row_idx = st.selectbox(
            "เลือกลูกค้าจากรายการที่พบ", 
            filtered_cus.index,
            format_func=lambda x: f"{filtered_cus.loc[x, 'รหัสลูกค้า']} | {filtered_cus.loc[x, 'ชื่อลูกค้า']}"
        )
        
        c_data = filtered_cus.loc[selected_row_idx]
        selected_cus_code = c_data['รหัสลูกค้า']
        selected_saleman_code = c_data['พนักงานขาย']
        default_unit = c_data['หน่วย']

        # --- ส่วนแสดงเงื่อนไขที่ปรับให้สวยงาม (ข้อ 2) ---
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #ff4b4b;">
            <h4 style="margin-top:0;">📋 ข้อมูลและเงื่อนไขการตรวจสอบ</h4>
            <table style="width:100%; border-collapse: collapse;">
                <tr>
                    <td style="width:20%; font-weight:bold; color:#555;">ลูกค้า:</td>
                    <td style="font-size:18px;">{selected_cus_code} | {c_data['ชื่อลูกค้า']}</td>
                </tr>
                <tr>
                    <td style="font-weight:bold; color:#555;">เงื่อนไข P/O:</td>
                    <td style="color:#d33682; font-weight:bold;">{c_data.get('เลขที่ P/O ลูกค้า', 'ไม่ระบุเงื่อนไข')}</td>
                </tr>
                <tr>
                    <td style="font-weight:bold; color:#555;">พนักงานขาย:</td>
                    <td>{c_data['ชื่อพนักงานขาย']} ({selected_saleman_code})</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_code_html=True)
        
        # แสดงรายการรหัสสินค้าจาก Master ที่เกี่ยวข้องเบื้องต้น
        if df_pd is not None:
            with st.expander("🔍 ดูรหัสสินค้าและ Barcode ใน Master ของลูกค้านี้"):
                col_map = "TUS" if "TUS" in selected_cus_code else "MAK" if "MAK" in selected_cus_code else "TFS"
                if col_map in df_pd.columns:
                    st.dataframe(df_pd[df_pd[col_map].notna()][['สินค้า', 'ชื่อสินค้า', col_map, 'Barcode']], use_container_width=True)

    else:
        st.warning("กรุณาระบุคำค้นหาเพื่อเลือกลูกค้า")

# 3. STEP 2: Upload & Parse (ปรับปรุงข้อ 1 และ 3)
st.markdown("---")
st.header("Step 2: Upload PO & Review")
uploaded_po = st.file_uploader("แนบไฟล์ PO (PDF/Excel)", type=['pdf', 'xlsx'])

if uploaded_po and df_pd is not None and not filtered_cus.empty:
    # (จำลองการดึงข้อมูล - ในเครื่องจริงส่วนนี้จะเชื่อมกับ Parser)
    # ข้อ 1: ถ้า Parse ไม่สำเร็จ/หาไม่เจอ จะยังแสดงแถวให้พี่นุ่นแก้ได้
    simulated_items = ["405456181", "UNKNOWN_CODE_999"] # ตัวอย่างรหัสที่เจอและไม่เจอ
    
    review_list = []
    for item in simulated_items:
        col_map = "TUS" if "TUS" in selected_cus_code else "MAK" if "MAK" in selected_cus_code else "TFS"
        match = df_pd[df_pd[col_map].astype(str).str.contains(item, na=False)] if col_map in df_pd.columns else pd.DataFrame()
        
        if match.empty:
            match = df_pd[(df_pd['Barcode'].astype(str) == item) | (df_pd['สินค้า'] == item)]

        if not match.empty:
            # Parse สำเร็จ
            res = match.iloc[0]
            review_list.append({
                "สินค้า (S-018)": res['สินค้า'],
                "ชื่อสินค้า": res['ชื่อสินค้า'],
                "จำนวนสั่ง (ราคา)": 0.0,
                "หน่วยราคา": default_unit,
                "Status": "✅ OK",
                "p_ratio": 1, # ค่าสมมติ
                "b_ratio": 1  # ค่าสมมติ
            })
        else:
            # Parse ไม่สำเร็จ (ข้อ 1: แก้ไขให้แสดงเพื่อให้พี่นุ่นแก้เองได้)
            review_list.append({
                "สินค้า (S-018)": item,
                "ชื่อสินค้า": "⚠️ ไม่พบ! กรุณาพิมพ์รหัสที่ถูกต้อง",
                "จำนวนสั่ง (ราคา)": 0.0,
                "หน่วยราคา": default_unit,
                "Status": "❌ ERROR"
            })

    # ตาราง Review ที่แก้ไขได้
    edited_df = st.data_editor(pd.DataFrame(review_list), num_rows="dynamic", use_container_width=True)

    if st.button("ยืนยันรายการลงตะกร้า"):
        st.session_state.po_bucket.append({"cus": selected_cus_code, "data": edited_df})
        st.success("บันทึกข้อมูลเรียบร้อย")

# 4. STEP 3: Export (คงเดิม)
if st.session_state.po_bucket:
    st.markdown("---")
    if st.button("Generate Combined S-018"):
        # Logic รวมไฟล์และ Export ตามเดิม...
        st.write("ระบบกำลังรวมไฟล์...")
