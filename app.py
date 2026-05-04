import streamlit as st
import pandas as pd # Ensure this is imported as pd

st.title("ระบบแปลง PO → S-018")

# File Uploaders
uploaded_cust = st.file_uploader("Upload Cus_SaleList.xlsx", type=['xlsx'])
uploaded_prod = st.file_uploader("Upload PD_pack.xlsx", type=['xlsx'])

if uploaded_cust and uploaded_prod:
    # Read Excel files using pandas 
    customers_df = pd.read_excel(uploaded_cust)
    products_df = pd.read_excel(uploaded_prod)

    # 1. Select Customer 
    cust_list = customers_df['รหัสลูกค้า'].unique() [cite: 1]
    selected_cust = st.selectbox("เลือกรหัสลูกค้า", cust_list) [cite: 1]

    # 2. Get Salesman and Default Unit 
    cust_info = customers_df[customers_df['รหัสลูกค้า'] == selected_cust].iloc[0] [cite: 1]
    salesman_name = cust_info['ชื่อพนักงานขาย'] [cite: 1]
    default_unit = cust_info['หน่วย'] [cite: 1, 4] # e.g., 'carton' or 'box'

    st.write(f"**พนักงานขาย:** {salesman_name}") [cite: 1]
    st.write(f"**หน่วย Default:** {default_unit}") [cite: 1]

    # 3. Filter Products by Default Unit 
    # Use capitalize to match "Carton/" or "Box/" in PD_pack 
    target_pattern = f"{default_unit.capitalize()}/" [cite: 7]
    
    # Filter rows where 'หน่วย' contains the pattern 
    matched_products = products_df[products_df['หน่วย'].str.contains(target_pattern, na=False)] [cite: 7]
    
    st.subheader(f"รายการสินค้า (หน่วย {target_pattern})")
    st.dataframe(matched_products[['สินค้า', 'ชื่อสินค้า', 'หน่วย', 'อัตราส่วน/หน่วยหลัก']]) [cite: 7]
else:
    st.info("กรุณาอัปโหลดไฟล์ Excel ทั้ง 2 ไฟล์ที่แถบเมนูด้านซ้าย")
