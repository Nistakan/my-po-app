import streamlit as st
import pandas as pd
import io
from datetime import datetime

# --- 1. CONFIG & SETUP ---
st.set_page_config(page_title="PO to S-018 Generator", layout="wide")

# Initialize Session State
if 'db_pd' not in st.session_state: st.session_state.db_pd = None
if 'db_cus' not in st.session_state: st.session_state.db_cus = None

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ ระบบจัดการข้อมูลหลัก")
    up_pd = st.file_uploader("Upload PD_pack.xlsx", type=["xlsx"])
    if up_pd:
        st.session_state.db_pd = pd.read_excel(up_pd)
        st.success("อัปเดตข้อมูลสินค้าแล้ว")
        
    up_cus = st.file_uploader("Upload Cus_SaleList.xlsx", type=["xlsx"])
    if up_cus:
        st.session_state.db_cus = pd.read_excel(up_cus)
        st.success("อัปเดตข้อมูลลูกค้าแล้ว")

# --- 3. MAIN WORKFLOW ---
st.title("📦 PO to Sales Order (S-018)")

if st.session_state.db_pd is None or st.session_state.db_cus is None:
    st.warning("⚠️ กรุณาอัปโหลดไฟล์ Master Data ทั้ง 2 ไฟล์ที่แถบด้านซ้ายก่อนนะคะ")
else:
    # เลือกชื่อลูกค้า
    cus_names = st.session_state.db_cus['ชื่อลูกค้า'].unique()
    selected_cus_name = st.selectbox("เลือกชื่อลูกค้า", cus_names)
    
    cus_row = st.session_state.db_cus[st.session_state.db_cus['ชื่อลูกค้า'] == selected_cus_name].iloc[0]
    customer_code = cus_row['รหัสลูกค้า']
    saleman_code = cus_row['พนักงานขาย']
    default_unit = str(cus_row['หน่วย']).lower()

    # อัปโหลด PO
    st.divider()
    po_file = st.file_uploader("อัปโหลดไฟล์ PO", type=["pdf", "xlsx", "png", "jpg"])

    if po_file:
        # [จำลองข้อมูลจากการ Parse]
        mock_po_item = "FSMT0101"
        mock_po_qty = 1 
        
        pd_master = st.session_state.db_pd
        
        try:
            # หา Ratio ของหน่วยราคา
            price_unit_rows = pd_master[(pd_master['สินค้า'] == mock_po_item) & 
                                       (pd_master['หน่วย'].str.contains(default_unit, case=False, na=False))]
            
            # หา Ratio ของหน่วย Box
            box_unit_rows = pd_master[(pd_master['สินค้า'] == mock_po_item) & 
                                     (pd_master['หน่วย'].str.contains('Box', case=False, na=False))]

            if not price_unit_rows.empty and not box_unit_rows.empty:
                # แปลงค่าเป็นตัวเลข ป้องกัน Error
                ratio_price = pd.to_numeric(price_unit_rows.iloc[0]['อัตราส่วน/หน่วยหลัก'], errors='coerce')
                ratio_box = pd.to_numeric(box_unit_rows.iloc[0]['อัตราส่วน/หน่วยหลัก'], errors='coerce')

                # เช็คว่า Ratio เป็นตัวเลขและไม่เป็น 0
                if pd.notnull(ratio_price) and pd.notnull(ratio_box) and ratio_box != 0:
                    calc_qty = (mock_po_qty * ratio_price) / ratio_box
                    st.success(f"คำนวณสำเร็จ: {calc_qty} กล่อง")
                else:
                    calc_qty = mock_po_qty
                    st.error("⚠️ ค่า Ratio ใน Master Data ไม่ใช่ตัวเลข หรือเป็นเลข 0 ค่ะ")
            else:
                calc_qty = mock_po_qty
                st.warning("⚠️ ไม่พบหน่วยที่ตรงกันใน Master Data")

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการคำนวณ: {e}")
            calc_qty = mock_po_qty

        # แสดงตาราง Review
        df_review = pd.DataFrame([{
            "สินค้า": mock_po_item,
            "จำนวนสั่ง (ราคา)": mock_po_qty,
            "จำนวนสั่ง-สินค้า": calc_qty,
            "เลขที่ P/O ลูกค้า": "PO-TEST"
        }])
        st.data_editor(df_review)
