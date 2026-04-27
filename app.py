import streamlit as st
import pandas as pd
import io
from datetime import datetime

# --- 1. CONFIG & SETUP ---
st.set_page_config(page_title="PO to S-018 Generator", layout="wide")

# ฟังก์ชันสำหรับจัดการไฟล์ (Overwrite Logic)
def save_data(df, key):
    st.session_state[key] = df

# Initialize Session State
if 'db_pd' not in st.session_state: st.session_state.db_pd = None
if 'db_cus' not in st.session_state: st.session_state.db_cus = None

# --- 2. SIDEBAR: MASTER DATA (OVERWRITE) ---
with st.sidebar:
    st.header("⚙️ ระบบจัดการข้อมูลหลัก")
    st.info("อัปโหลดไฟล์เพื่อ Overwrite ข้อมูลเดิม")
    
    up_pd = st.file_uploader("Upload PD_pack.xlsx", type=["xlsx", "csv"])
    if up_pd:
        df_pd = pd.read_csv(up_pd) if up_pd.name.endswith('.csv') else pd.read_excel(up_pd)
        save_data(df_pd, 'db_pd')
        st.success("อัปเดตข้อมูลสินค้าแล้ว")
        
    up_cus = st.file_uploader("Upload Cus_SaleList.xlsx", type=["xlsx", "csv"])
    if up_cus:
        df_cus = pd.read_csv(up_cus) if up_cus.name.endswith('.csv') else pd.read_excel(up_cus)
        save_data(df_cus, 'db_cus')
        st.success("อัปเดตข้อมูลลูกค้าแล้ว")

# --- 3. MAIN WORKFLOW ---
st.title("📦 PO to Sales Order (S-018)")

if st.session_state.db_pd is None or st.session_state.db_cus is None:
    st.warning("⚠️ กรุณาอัปโหลดไฟล์ Master Data ที่ Sidebar ด้านซ้ายก่อนค่ะ")
else:
    # STEP 1: User Pre-selection
    st.subheader("Step 1: ข้อมูลลูกค้าและพนักงานขาย")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # ดึงรายชื่อลูกค้าจาก Master
        cus_names = st.session_state.db_cus['ชื่อลูกค้า'].unique()
        selected_cus_name = st.selectbox("เลือกชื่อลูกค้า", cus_names)
        
        # ดึงข้อมูลรหัสลูกค้าและเซลล์
        cus_row = st.session_state.db_cus[st.session_state.db_cus['ชื่อลูกค้า'] == selected_cus_name].iloc[0]
        customer_code = cus_row['รหัสลูกค้า']
        saleman_code = cus_row['พนักงานขาย']
        default_unit = cus_row['หน่วย'] # เช่น carton, box, pcs

    with col2:
        st.text_input("รหัสพนักงานขาย", value=saleman_code, disabled=True)
    with col3:
        price_unit_input = st.text_input("หน่วยราคาตั้งต้น (จากลูกค้า)", value=default_unit, disabled=True)

    # STEP 2: Upload PO
    st.divider()
    st.subheader("Step 2: อัปโหลดไฟล์ PO")
    po_file = st.file_uploader("ลากไฟล์ PO มาวางที่นี่", type=["pdf", "xlsx", "png", "jpg"])

    if po_file:
        # --- 4. CRITICAL LOGIC (MAPPING & CALCULATION) ---
        st.subheader("📝 ตรวจสอบข้อมูลก่อน Export (Review)")
        
        # [จำลองการ Parse จาก PO - ในแอปจริงส่วนนี้จะเชื่อม Gemini]
        # ตัวอย่าง: สั่ง 1 Carton สินค้า FSMT0101
        mock_po_item = "FSMT0101"
        mock_po_qty = 1 # สั่ง 1 ลัง
        
        # -- ค้นหาข้อมูลใน Master PD_pack --
        pd_master = st.session_state.db_pd
        
        # หา Ratio ของหน่วยราคา (Price Unit)
        # เช่น หาบรรทัดที่เป็น 'Carton/540' เพื่อเอา Ratio 540
        price_unit_row = pd_master[(pd_master['สินค้า'] == mock_po_item) & 
                                   (pd_master['หน่วย'].str.contains(default_unit, case=False))].iloc[0]
        ratio_price = price_unit_row['อัตราส่วน/หน่วยหลัก']
        price_unit_full_name = price_unit_row['หน่วย']
        
        # หา Ratio ของหน่วย Box (Standard Box)
        # เช่น หาบรรทัดที่มีคำว่า 'Box'
        box_unit_row = pd_master[(pd_master['สินค้า'] == mock_po_item) & 
                                 (pd_master['หน่วย'].str.contains('Box', case=False))].iloc[0]
        ratio_box = box_unit_row['อัตราส่วน/หน่วยหลัก']
        box_unit_full_name = box_unit_row['หน่วย']

        # คำนวณ จำนวนสั่ง-สินค้า
        # สูตร: (Qty จาก PO * Ratio หน่วยราคา) / Ratio หน่วย Box
        calc_qty = (mock_po_qty * ratio_price) / ratio_box

        # สร้าง DataFrame สำหรับหน้า Review
        review_data = {
            "สินค้า": [mock_po_item],
            "จำนวนสั่ง (ราคา)": [mock_po_qty],
            "หน่วยราคา": [price_unit_full_name],
            "หน่วย": [box_unit_full_name],
            "จำนวนสั่ง-สินค้า": [calc_qty],
            "เลขที่ P/O ลูกค้า": ["PO-881000"]
        }
        df_review = pd.DataFrame(review_data)
        
        # ให้พี่นุ่นแก้ได้ในตาราง
        edited_df = st.data_editor(df_review, num_rows="dynamic")

        # STEP 3: Export to S-018
        if st.button("🚀 สร้างไฟล์ S-018 และดาวน์โหลด"):
            # สร้างไฟล์ Excel ใน Memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # สร้างโครงตาม Template S-018 ที่พี่นุ่นให้มา
                final_columns = [
                    'เลขที่สั่งขาย','วันที่สั่งขาย','ยืนยัน','ลูกค้า','ประเภทใบสั่งขาย','พนักงานขาย',
                    'แผนก','เลขที่ P/O ลูกค้า','วันที่ P/O ลูกค้า','วันที่ต้องการ','ประเภทเอกสาร',
                    'ประเภทความต้องการ','Def.แผนกเบิก','หมายเหตุ','ลำดับ-สินค้า','สินค้า','หน่วย',
                    'จำนวนสั่ง-สินค้า','หน่วยราคา','จำนวนสั่ง (ราคา)','ราคาขาย','%ส่วนลด','%ส่วนลด2',
                    'ส่วนลด/หน่วย','%ส่วนลดพิเศษ','ของแถม','หมายเหตุ-สินค้า'
                ]
                
                # เตรียมข้อมูลหยอดลง Column
                export_df = pd.DataFrame(columns=final_columns)
                for index, row in edited_df.iterrows():
                    new_row = {
                        'ยืนยัน': 'N|สร้างใหม่',
                        'ลูกค้า': customer_code,
                        'ประเภทใบสั่งขาย': '1|ขายจากคลัง',
                        'พนักงานขาย': saleman_code,
                        'แผนก': 'SEL',
                        'เลขที่ P/O ลูกค้า': row['เลขที่ P/O ลูกค้า'],
                        'ลำดับ-สินค้า': index + 1,
                        'สินค้า': row['สินค้า'],
                        'หน่วย': row['หน่วย'],
                        'จำนวนสั่ง-สินค้า': row['จำนวนสั่ง-สินค้า'],
                        'หน่วยราคา': row['หน่วยราคา'],
                        'จำนวนสั่ง (ราคา)': row['จำนวนสั่ง (ราคา)'],
                        'ของแถม': 'N|No'
                    }
                    export_df = pd.concat([export_df, pd.DataFrame([new_row])], ignore_index=True)
                
                export_df.to_excel(writer, index=False, sheet_name='Sheet1')
            
            st.success("สร้างไฟล์สำเร็จ!")
            st.download_button(
                label="📥 Click เพื่อดาวน์โหลด S-018",
                data=output.getvalue(),
                file_name=f"S-018_{selected_cus_name}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )