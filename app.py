import streamlit as st
import pandas as pd
import io
import re
from datetime import datetime

# --- 1. CONFIG & SETUP ---
st.set_page_config(page_title="PO to S-018 Generator", layout="wide")

if 'db_pd' not in st.session_state: st.session_state.db_pd = None
if 'db_cus' not in st.session_state: st.session_state.db_cus = None

# --- 2. SIDEBAR: MASTER DATA ---
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
    st.warning("⚠️ กรุณาอัปโหลดไฟล์ Master Data ทั้ง 2 ไฟล์ที่ด้านซ้ายก่อนค่ะ")
else:
    # --- STEP 1: เลือกพนักงานและลูกค้า (ไม่สนตัวพิมพ์เล็ก-ใหญ่) ---
    st.subheader("Step 1: ข้อมูลลูกค้าและพนักงานขาย")
    
    # รวมรหัสและชื่อลูกค้าให้เลือกง่ายๆ
    cus_df = st.session_state.db_cus.copy()
    cus_df['Cus_Select'] = cus_df['รหัสลูกค้า'].astype(str) + " : " + cus_df['ชื่อลูกค้า'].astype(str)
    
    selected_cus_str = st.selectbox("เลือกรหัสหรือชื่อลูกค้า (MT-TFS...)", cus_df['Cus_Select'].unique())
    selected_cus_code = selected_cus_str.split(" : ")[0]
    
    # ดึงข้อมูลพนักงานขายจากลูกค้าที่เลือก
    row_cus = cus_df[cus_df['รหัสลูกค้า'] == selected_cus_code].iloc[0]
    
    col1, col2 = st.columns(2)
    with col1:
        saleman = st.text_input("รหัสพนักงานขาย / ชื่อ", value=f"{row_cus['พนักงานขาย']} : {row_cus['ชื่อพนักงานขาย']}")
    with col2:
        default_unit = st.text_input("หน่วยราคาตั้งต้น", value=row_cus['หน่วย'], disabled=True)

    # --- STEP 2: อัปโหลดและ Parsing PO ---
    st.divider()
    po_file = st.file_uploader("อัปโหลดไฟล์ PO (PDF/Excel)", type=["pdf", "xlsx", "png", "jpg"])

    if po_file:
        st.subheader("📝 ตรวจสอบและเลือกหน่วยสินค้า (Review)")
        
        # [สมมติค่าที่ดึงได้จาก PO]
        raw_po_number = "881.2345" # ตัวอย่างเลขที่ PO
        raw_product_code = "8906371" # รหัสสินค้าจากลูกค้า
        raw_qty = 10 # จำนวนที่สั่ง
        
        # --- Logic ดึงเลขที่ PO ---
        clean_po = ""
        if "881." in raw_po_number: clean_po = raw_po_number # Makro
        elif raw_po_number.startswith("4") and len(raw_po_number) == 8: clean_po = raw_po_number # Lotus
        elif raw_po_number.startswith("T") and len(raw_po_number) == 10: clean_po = raw_po_number # TFS
        else: clean_po = raw_po_number

        # --- Mapping สินค้า ---
        pd_master = st.session_state.db_pd
        # ค้นหาจากรหัสลูกค้า (Mak, Tus, Tfs) แบบไม่สนชื่อ Column
        match_pd = pd_master[(pd_master['Mak'].astype(str) == raw_product_code) | 
                             (pd_master['Tus'].astype(str) == raw_product_code) | 
                             (pd_master['Tfs'].astype(str) == raw_product_code)]

        if not match_pd.empty:
            product_code_internal = match_pd.iloc[0]['สินค้า']
            product_name = match_pd.iloc[0]['ชื่อสินค้า']
            
            # ถ้ามีหลายหน่วย ให้สร้าง Dropdown
            all_units = match_pd['หน่วย'].unique().tolist()
            
            st.write(f"**สินค้าที่พบ:** {product_code_internal} - {product_name}")
            selected_unit = st.selectbox("พบหลายหน่วย กรุณาเลือกหน่วยที่ถูกต้อง:", all_units)
            
            # ดึง Ratio ของหน่วยที่เลือก
            chosen_row = match_pd[match_pd['หน่วย'] == selected_unit].iloc[0]
            ratio_price = chosen_row['อัตราส่วน/หน่วยหลัก']
            
            # หาหน่วย Box เพื่อคำนวณจำนวนสั่ง-สินค้า
            box_row = pd_master[(pd_master['สินค้า'] == product_code_internal) & 
                                (pd_master['หน่วย'].str.contains('Box', case=False, na=False))]
            
            ratio_box = box_row.iloc[0]['อัตราส่วน/หน่วยหลัก'] if not box_row.empty else ratio_price
            calc_qty = (raw_qty * ratio_price) / ratio_box

            # --- STEP 3: สร้างตารางและ Export ---
            review_df = pd.DataFrame([{
                "เลขที่ P/O ลูกค้า": clean_po,
                "สินค้า": product_code_internal,
                "หน่วย": selected_unit,
                "จำนวนสั่ง-สินค้า": calc_qty,
                "หน่วยราคา": selected_unit,
                "จำนวนสั่ง (ราคา)": raw_qty
            }])
            
            st.data_editor(review_df)

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                # ปุ่ม Download ปกติ
                st.download_button("📥 Download S-018 Excel", data=b"...", file_name="S-018.xlsx")
            with col_btn2:
                # ปุ่ม API (จำลอง)
                if st.button("🚀 Send to ERP API"):
                    st.success("ส่งข้อมูลเข้าระบบ ERP เรียบร้อยแล้ว!")
