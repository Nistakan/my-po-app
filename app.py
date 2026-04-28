import streamlit as st
import pandas as pd
from datetime import datetime
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="PO to S-018 Generator", layout="wide")

# --- HELPER FUNCTIONS ---
def load_master_data(file):
    if file is not None:
        return pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
    return None

def normalize_unit_logic(po_qty, price_unit_ratio, box_unit_ratio):
    """สูตร: (จำนวนสั่งจาก PO × Ratio หน่วยราคา) ÷ Ratio หน่วย Box"""
    try:
        po_qty = float(po_qty)
        p_ratio = float(price_unit_ratio)
        b_ratio = float(box_unit_ratio)
        return (po_qty * p_ratio) / b_ratio
    except:
        return 0

# --- MAIN APP ---
st.title("📦 PO to Sales Order (S-018) Generator")
st.markdown("---")

# 1. SIDEBAR: Master Data Management
with st.sidebar:
    st.header("⚙️ Master Data Management")
    uploaded_cus = st.file_uploader("Upload Cus_SaleList", type=['xlsx', 'csv'])
    uploaded_pd = st.file_uploader("Upload PD_pack", type=['xlsx', 'csv'])
    
    if uploaded_cus and uploaded_pd:
        st.success("Master Data Loaded!")

# 2. STEP 1: Pre-selection (เลือกพนักงานขายและลูกค้า)
st.header("Step 1: Selection & Upload PO")
col1, col2, col3 = st.columns(3)

df_cus = load_master_data(uploaded_cus)
df_pd = load_master_data(uploaded_pd)

selected_cus = None
default_unit = "pcs"
selected_saleman = ""

if df_cus is not None:
    with col1:
        customer_list = df_cus['ชื่อลูกค้า'].unique()
        selected_cus_name = st.selectbox("เลือกชื่อลูกค้า", customer_list)
        cus_info = df_cus[df_cus['ชื่อลูกค้า'] == selected_cus_name].iloc[0]
        selected_cus_code = cus_info['รหัสลูกค้า']
        default_unit = cus_info['หน่วย']
    
    with col2:
        saleman_list = df_cus[df_cus['ชื่อลูกค้า'] == selected_cus_name]['ชื่อพนักงานขาย'].unique()
        selected_saleman_name = st.selectbox("เลือกพนักงานขาย", saleman_list)
        selected_saleman_code = df_cus[df_cus['ชื่อพนักงานขาย'] == selected_saleman_name].iloc[0]['พนักงานขาย']

# 3. STEP 2: PO Upload & Parsing (Simulated for this script)
with col3:
    uploaded_po = st.file_uploader("Upload PO File (PDF/Excel)", type=['pdf', 'xlsx'])

if uploaded_po and df_pd is not None:
    st.markdown("---")
    st.header("Step 2: Review & Edit Data")
    
    # จำลองข้อมูลจากการ Parse (ในแอปจริงส่วนนี้จะเรียก Gemini API)
    # ตัวอย่างข้อมูลจำลองจากเคส Lotus ที่พี่นุ่นให้มา
    raw_po_data = [
        {"po_item": "405456181", "qty": 28, "po_no": "35037492"}, # FSMT1001 (Match 185)
        {"po_item": "405456179", "qty": 10, "po_no": "35037492"},
        {"po_item": "407677149", "qty": 36, "po_no": "35037492"},
        {"po_item": "999999999", "qty": 5, "po_no": "35037492"}   # ตัวอย่างรายการไม่พบรหัส
    ]
    
    review_list = []
    
    for item in raw_po_data:
        # Priority 1: Customer Code (TUS/MAK/TFS)
        col_name = ""
        if "TUS" in selected_cus_code: col_name = "TUS"
        elif "MAK" in selected_cus_code: col_name = "MAK"
        
        # ค้นหาใน Master
        match = df_pd[df_pd[col_name].astype(str).str.contains(item['po_item'], na=False)] if col_name else pd.DataFrame()
        
        # Priority 2: Barcode/GMT Code
        if match.empty:
            match = df_pd[(df_pd['Barcode'].astype(str) == item['po_item']) | (df_pd['สินค้า'] == item['po_item'])]

        if not match.empty:
            gmt_code = match.iloc[0]['สินค้า']
            product_name = match.iloc[0]['ชื่อสินค้า']
            
            # หา Ratio ของหน่วยราคา (Price Unit)
            p_ratio_row = df_pd[(df_pd['สินค้า'] == gmt_code) & (df_pd['หน่วย'].str.contains(default_unit, case=False))]
            p_ratio = p_ratio_row.iloc[0]['อัตราส่วน/หน่วยหลัก'] if not p_ratio_row.empty else 1
            
            # หา Ratio ของหน่วย Box
            b_ratio_row = df_pd[(df_pd['สินค้า'] == gmt_code) & (df_pd['หน่วย'].str.contains("Box", case=False))]
            b_unit = b_ratio_row.iloc[0]['หน่วย'] if not b_ratio_row.empty else "N/A"
            b_ratio = b_ratio_row.iloc[0]['อัตราส่วน/หน่วยหลัก'] if not b_ratio_row.empty else 0
            
            calc_qty = normalize_unit_logic(item['qty'], p_ratio, b_ratio)
            
            review_list.append({
                "สินค้า (S-018)": gmt_code,
                "ชื่อสินค้า": product_name,
                "จำนวนสั่ง (ราคา)": item['qty'],
                "หน่วยราคา": f"{default_unit.capitalize()}/{int(p_ratio)}",
                "จำนวนสั่ง-สินค้า": calc_qty,
                "หน่วย": b_unit,
                "Status": "✅ OK"
            })
        else:
            review_list.append({
                "สินค้า (S-018)": item['po_item'],
                "ชื่อสินค้า": "❌ ไม่พบรหัสใน Master",
                "จำนวนสั่ง (ราคา)": item['qty'],
                "หน่วยราคา": default_unit,
                "จำนวนสั่ง-สินค้า": 0,
                "หน่วย": "N/A",
                "Status": "❌ ERROR"
            })

    # แสดงตาราง Review
    df_review = pd.DataFrame(review_list)
    
    def highlight_error(s):
        return ['background-color: #ffcccc' if s.Status == "❌ ERROR" else '' for _ in s]

    st.table(df_review.style.apply(highlight_error, axis=1))

    # 4. STEP 3: Export S-018
    st.markdown("---")
    st.header("Step 3: Export S-018")
    
    if st.button("Generate S-018 Excel File"):
        # สร้าง Template จำลอง
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # สร้างโครงสร้างคอลัมน์ให้ตรงตาม S-018 (27 คอลัมน์)
            s018_final = pd.DataFrame(columns=[
                'เลขที่สั่งขาย', 'วันที่สั่งขาย', 'ยืนยัน', 'ลูกค้า', 'ประเภทใบสั่งขาย', 
                'พนักงานขาย', 'แผนก', 'เลขที่ P/O ลูกค้า', 'วันที่ P/O ลูกค้า', 'วันที่ต้องการ',
                'ประเภทเอกสาร', 'ประเภทความต้องการ', 'Def.แผนกเบิก', 'หมายเหตุ', 'ลำดับ-สินค้า',
                'สินค้า', 'หน่วย', 'จำนวนสั่ง-สินค้า', 'หน่วยราคา', 'จำนวนสั่ง (ราคา)', 'ของแถม'
            ])
            
            for i, row in df_review.iterrows():
                if row['Status'] == "✅ OK":
                    s018_final.loc[i] = [
                        f"SO-{i+1}", datetime.now().strftime("%d/%m/%Y"), "Y|ยืนยัน", selected_cus_code,
                        "1|ขายจากคลัง", selected_saleman_code, "SEL", item['po_no'], "", "",
                        "ขายโมเดิร์นเทรด", "2|ไม่ยืนยัน", "", "", i+1,
                        row['สินค้า (S-018)'], row['หน่วย'], row['จำนวนสั่ง-สินค้า'], 
                        row['หน่วยราคา'], row['จำนวนสั่ง (ราคา)'], "N|No"
                    ]
            
            s018_final.to_excel(writer, index=False, sheet_name='Sheet1')
        
        st.download_button(
            label="⬇️ Download S-018.xlsx",
            data=output.getvalue(),
            file_name=f"S018_{selected_cus_code}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("💡 กรุณาอัปโหลด Master Data และเลือกข้อมูลให้ครบเพื่อเริ่มทำงานค่ะ")
