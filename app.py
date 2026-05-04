import streamlit as st
import pandas as pd

st.title("ระบบแปลง PO → S-018 (Excel Master)")

# --- ส่วนการจัดการไฟล์ Master (XLSX) ---
st.sidebar.header("📁 ตั้งค่าไฟล์ Master (.xlsx)")
uploaded_cust = st.sidebar.file_uploader("อัปโหลดไฟล์ Cus_SaleList.xlsx", type=['xlsx'])
uploaded_prod = st.sidebar.file_uploader("อัปโหลดไฟล์ PD_pack.xlsx", type=['xlsx'])

if uploaded_cust and uploaded_prod:
    # 1. โหลดข้อมูลจาก Excel
    # ใช้ engine='openpyxl' เพื่อรองรับไฟล์ .xlsx
    customers_df = pd.read_excel(uploaded_cust) [cite: 1]
    products_df = pd.read_excel(uploaded_prod) [cite: 7]

    # --- UI การเลือกลูกค้า ---
    st.subheader("1. กำหนดข้อมูลลูกค้าและพนักงานขาย")
    
    # รายชื่อรหัสลูกค้า 
    cust_list = customers_df['รหัสลูกค้า'].unique() 
    selected_cust_code = st.selectbox("เลือกรหัสลูกค้า", cust_list)

    # ดึงข้อมูลลูกค้าที่เลือก 
    cust_data = customers_df[customers_df['รหัสลูกค้า'] == selected_cust_code].iloc[0]
    
    salesman_code = cust_data['พนักงานขาย'] [cite: 1]
    salesman_name = cust_data['ชื่อพนักงานขาย'] [cite: 1]
    default_unit = cust_data['หน่วย']  # 'box' หรือ 'carton' 

    # แสดงผลพนักงานขายและหน่วย Default ของลูกค้านั้นๆ
    col1, col2, col3 = st.columns(3)
    col1.metric("พนักงานขาย", salesman_name) [cite: 1]
    col2.metric("รหัสพนักงาน", salesman_code) [cite: 1]
    col3.metric("หน่วยตั้งต้น (Default)", default_unit) [cite: 1]

    # --- Logic การดึงหน่วยสินค้าตาม Default Unit ---
    st.subheader("2. ตัวอย่างการ Map สินค้าตามหน่วยที่เลือก")
    
    # กำหนด Keyword เช่น 'Carton/' หรือ 'Box/' 
    target_search = default_unit.capitalize() + "/" 
    
    # ค้นหาแถวใน PD_pack ที่ตรงกับหน่วยที่ต้องการ 
    matched_units = products_df[products_df['หน่วย'].str.contains(target_search, na=False)] 
    
    if not matched_units.empty:
        st.success(f"ระบบจะเลือกใช้หน่วยที่ขึ้นต้นด้วย '{target_search}' จาก MasterProduct อัตโนมัติ") [cite: 7]
        st.dataframe(matched_units[['สินค้า', 'ชื่อสินค้า', 'หน่วย', 'อัตราส่วน/หน่วยหลัก']].head(10)) [cite: 7]
    else:
        st.error(f"ไม่พบหน่วยที่ตรงกับ '{target_search}' ในไฟล์ PD_pack")

else:
    st.info("กรุณาอัปโหลดไฟล์ Excel ทั้ง 2 ไฟล์ที่แถบเมนูด้านซ้าย")
