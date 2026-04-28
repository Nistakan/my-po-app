import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="PO to S-018 Generator", layout="wide")

# Initialize Session State สำหรับเก็บ PO หลายใบ
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

# 1. SIDEBAR: Master Data Management
with st.sidebar:
    st.header("⚙️ Master Data Management")
    uploaded_cus = st.file_uploader("Upload Cus_SaleList", type=['xlsx', 'csv'])
    uploaded_pd = st.file_uploader("Upload PD_pack", type=['xlsx', 'csv'])
    if st.button("Clear All POs in Bucket"):
        st.session_state.po_bucket = []
        st.rerun()

df_cus = load_master_data(uploaded_cus)
df_pd = load_master_data(uploaded_pd)

# 2. STEP 1: Selection (ปรับปรุงการค้นหาลูกค้าและแสดงผล)
st.header("Step 1: Customer & PO Info")
col1, col2 = st.columns(2)

if df_cus is not None:
    with col1:
        # ค้นหาแบบไม่สนอักษรเล็กใหญ่
        search_term = st.text_input("ค้นหาลูกค้า (รหัส หรือ ชื่อ)").strip().lower()
        
        # Filter ข้อมูลลูกค้า
        mask = df_cus['รหัสลูกค้า'].str.lower().str.contains(search_term) | \
               df_cus['ชื่อลูกค้า'].str.lower().str.contains(search_term)
        filtered_cus = df_cus[mask]

        if not filtered_cus.empty:
            # แสดงข้อมูลที่พบ
            selected_row = st.selectbox(
                "เลือกลูกค้าที่ถูกต้อง", 
                filtered_cus.index,
                format_func=lambda x: f"{filtered_cus.loc[x, 'รหัสลูกค้า']} | {filtered_cus.loc[x, 'ชื่อลูกค้า']} (เซลล์: {filtered_cus.loc[x, 'ชื่อพนักงานขาย']})"
            )
            
            # ดึงข้อมูลสำคัญเก็บไว้
            c_data = filtered_cus.loc[selected_row]
            selected_cus_code = c_data['รหัสลูกค้า']
            selected_cus_name = c_data['ชื่อลูกค้า']
            selected_saleman_name = c_data['ชื่อพนักงานขาย']
            selected_saleman_code = c_data['พนักงานขาย']
            default_unit = c_data['หน่วย']
            
            st.info(f"📍 **ลูกค้า:** {selected_cus_code} | **เซลล์:** {selected_saleman_name}")
        else:
            st.warning("ไม่พบข้อมูลลูกค้า")

    with col2:
        # 3. Pre-parsing Logic (เลขที่ PO และ รหัสสินค้า)
        input_po_no = st.text_input("ระบุเลขที่ P/O ลูกค้า (เช่น 4xxxxxxx หรือ 881.x)")
        input_product_ref = st.text_area("ระบุรหัสสินค้า/Barcode (ถ้ามีหลายรายการให้เว้นบรรทัด)")
        uploaded_po = st.file_uploader("แนบไฟล์ PO เพื่อยืนยัน (PDF/Excel)", type=['pdf', 'xlsx'])

# 4. STEP 2: Review & Edit Data (เก็บแยกไฟล์ก่อนรวม)
if uploaded_po and df_pd is not None and not filtered_cus.empty:
    st.markdown("---")
    st.header(f"Step 2: Review PO No: {input_po_no}")
    
    # [Simulated Parsing Logic based on input_product_ref]
    items_to_review = [line.strip() for line in input_product_ref.split('\n') if line.strip()]
    review_list = []
    
    for item in items_to_review:
        # Mapping Logic เดิมที่สั่งไว้ (TUS 9 หลักขึ้นต้นด้วย 4 / MAK 6 หลัก)
        col_map = "TUS" if "TUS" in selected_cus_code else "MAK" if "MAK" in selected_cus_code else "TFS"
        
        match = df_pd[df_pd[col_map].astype(str).str.contains(item, na=False)] if col_map in df_pd.columns else pd.DataFrame()
        if match.empty:
            match = df_pd[(df_pd['Barcode'].astype(str) == item) | (df_pd['สินค้า'] == item)]

        if not match.empty:
            gmt_code = match.iloc[0]['สินค้า']
            p_ratio_row = df_pd[(df_pd['สินค้า'] == gmt_code) & (df_pd['หน่วย'].str.contains(default_unit, case=False))]
            p_ratio = p_ratio_row.iloc[0]['อัตราส่วน/หน่วยหลัก'] if not p_ratio_row.empty else 1
            b_ratio_row = df_pd[(df_pd['สินค้า'] == gmt_code) & (df_pd['หน่วย'].str.contains("Box", case=False))]
            
            review_list.append({
                "PO_No": input_po_no,
                "สินค้า (S-018)": gmt_code,
                "ชื่อสินค้า": match.iloc[0]['ชื่อสินค้า'],
                "จำนวนสั่ง (ราคา)": 0.0, # รอพี่นุ่นกรอกในตาราง
                "หน่วยราคา": f"{default_unit}/{int(p_ratio)}",
                "หน่วย": b_ratio_row.iloc[0]['หน่วย'] if not b_ratio_row.empty else "Box",
                "p_ratio": p_ratio,
                "b_ratio": b_ratio_row.iloc[0]['อัตราส่วน/หน่วยหลัก'] if not b_ratio_row.empty else 1,
                "Status": "✅ OK"
            })
        else:
            review_list.append({"PO_No": input_po_no, "สินค้า (S-018)": item, "ชื่อสินค้า": "❌ ไม่พบรหัส", "Status": "❌ ERROR"})

    df_review = st.data_editor(pd.DataFrame(review_list), num_rows="dynamic")

    if st.button("ยืนยัน Review และเก็บลงตะกร้า"):
        # คำนวณจำนวนสั่ง-สินค้ายืนพื้นตาม Normalization ก่อนเก็บ
        df_review['จำนวนสั่ง-สินค้า'] = df_review.apply(lambda r: normalize_unit_logic(r['จำนวนสั่ง (ราคา)'], r.get('p_ratio',1), r.get('b_ratio',1)), axis=1)
        st.session_state.po_bucket.append({
            "cus_code": selected_cus_code,
            "saleman": selected_saleman_code,
            "po_no": input_po_no,
            "data": df_review[df_review['Status'] == "✅ OK"]
        })
        st.success(f"เก็บ PO: {input_po_no} เรียบร้อย! (รวมในตะกร้า {len(st.session_state.po_bucket)} ใบ)")

# 5. STEP 3: Export (รวมทุก PO เป็นไฟล์เดียว)
if st.session_state.po_bucket:
    st.markdown("---")
    st.header(f"Step 3: Export Consolidated S-018 ({len(st.session_state.po_bucket)} POs)")
    
    if st.button("Generate Combined S-018"):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final_rows = []
            for entry in st.session_state.po_bucket:
                for i, row in entry['data'].iterrows():
                    final_rows.append({
                        'เลขที่ P/O ลูกค้า': entry['po_no'],
                        'ลูกค้า': entry['cus_code'],
                        'พนักงานขาย': entry['saleman'],
                        'ยืนยัน': 'Y|ยืนยัน',
                        'ประเภทใบสั่งขาย': '1|ขายจากคลัง',
                        'แผนก': 'SEL',
                        'สินค้า': row['สินค้า (S-018)'],
                        'หน่วย': row['หน่วย'],
                        'จำนวนสั่ง-สินค้า': row['จำนวนสั่ง-สินค้า'],
                        'หน่วยราคา': row['หน่วยราคา'],
                        'จำนวนสั่ง (ราคา)': row['จำนวนสั่ง (ราคา)']
                    })
            
            df_final = pd.DataFrame(final_rows)
            df_final.to_excel(writer, index=False)
        
        st.download_button("⬇️ Download Combined S-018.xlsx", output.getvalue(), "S018_Combined.xlsx")
