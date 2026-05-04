import streamlit as st
import pandas as pd

st.title("ระบบแปลง PO → S-018")

# --- ส่วนการจัดการไฟล์ Master ---
st.sidebar.header("📁 ตั้งค่าไฟล์ Master")
uploaded_cust = st.sidebar.file_uploader("อัปโหลดไฟล์ Cus_SaleList (.csv)", type=['csv'])
uploaded_prod = st.sidebar.file_uploader("อัปโหลดไฟล์ PD_pack (.csv)", type=['csv'])

if uploaded_cust and uploaded_prod:
    # โหลดข้อมูลจากไฟล์ที่ผู้ใช้อัปโหลด 
    customers_df = pd.read_csv(uploaded_cust)
    products_df = pd.read_csv(uploaded_prod)

    # --- UI การเลือกลูกค้า ---
    st.subheader("1. เลือกข้อมูลลูกค้า")
    # ดึงรายชื่อรหัสลูกค้าที่มีทั้งหมด 
    cust_list = customers_df['รหัสลูกค้า'].unique()
    selected_cust_code = st.selectbox("เลือกรหัสลูกค้า", cust_list)

    # กรองข้อมูลลูกค้าที่เลือก 
    cust_data = customers_df[customers_df['รหัสลูกค้า'] == selected_cust_code].iloc[0]
    
    # ดึงค่าพนักงานขายและหน่วย Default 
    salesman_code = cust_data['พนักงานขาย']
    salesman_name = cust_data['ชื่อพนักงานขาย']
    default_unit = cust_data['หน่วย']  # 'box' หรือ 'carton' 

    # แสดงผลข้อมูลที่เลือกให้ผู้ใช้เห็น
    col1, col2, col3 = st.columns(3)
    col1.metric("พนักงานขาย", salesman_name)
    col2.metric("รหัสพนักงาน", salesman_code)
    col3.metric("หน่วย Default", default_unit)

    # --- Logic การดึงหน่วยสินค้า (Carton/xxx หรือ Box/xxx) ---
    st.subheader("2. ตรวจสอบหน่วยสินค้าใน Master")
    
    # ตัวอย่างการดึงหน่วยจาก PD_pack 
    # สมมติสินค้าคือ FSMT1001 และ User เลือกหน่วย default เป็น 'carton'
    target_search = default_unit.capitalize() + "/" # เช่น 'Carton/'
    
    # ค้นหาในไฟล์สินค้า 
    # เลือกแถวที่มีหน่วยขึ้นต้นด้วยคำที่กำหนด 
    matched_units = products_df[products_df['หน่วย'].str.contains(target_search, na=False)]
    
    st.write(f"รายการสินค้าที่ตรงกับหน่วย **{default_unit}** (ตัวอย่าง 5 รายการแรก):")
    st.dataframe(matched_units[['สินค้า', 'ชื่อสินค้า', 'หน่วย', 'อัตราส่วน/หน่วยหลัก']].head())

else:
    st.warning("กรุณาอัปโหลดไฟล์ Cus_SaleList.csv และ PD_pack.csv ที่แถบด้านซ้ายก่อนเริ่มทำงาน")
