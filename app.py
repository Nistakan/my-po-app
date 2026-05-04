import streamlit as st
import pandas as pd

st.set_page_config(page_title="PO to S-018 Converter", layout="wide")

st.title("🚀 ระบบแปลง PO → S-018")
st.markdown("---")

# --- 1. การจัดการไฟล์ Master Data ---
st.sidebar.header("📁 ส่วนการอัปโหลดไฟล์ Master")
uploaded_cust = st.sidebar.file_uploader("1. อัปโหลด Cus_SaleList.xlsx", type=['xlsx'])
uploaded_prod = st.sidebar.file_uploader("2. อัปโหลด PD_pack.xlsx", type=['xlsx'])

if uploaded_cust and uploaded_prod:
    try:
        # อ่านไฟล์ Excel 
        customers_df = pd.read_excel(uploaded_cust)
        products_df = pd.read_excel(uploaded_prod)

        # ลบช่องว่างในชื่อคอลัมน์เพื่อป้องกัน NameError/KeyError
        customers_df.columns = customers_df.columns.str.strip()
        products_df.columns = products_df.columns.str.strip()

        # --- 2. การเลือกลูกค้าและดึงข้อมูลที่เกี่ยวข้อง ---
        st.subheader("📍 1. ข้อมูลลูกค้าและเงื่อนไขการขาย")
        
        # ตรวจสอบคอลัมน์ 'รหัสลูกค้า' 
        if 'รหัสลูกค้า' in customers_df.columns:
            cust_list = customers_df['รหัสลูกค้า'].unique()
            selected_cust = st.selectbox("เลือกรหัสลูกค้า", cust_list)

            # กรองข้อมูลลูกค้า 
            cust_info = customers_df[customers_df['รหัสลูกค้า'] == selected_cust].iloc[0]
            
            # ดึงข้อมูลพนักงานขายและหน่วย Default 
            salesman_name = cust_info.get('ชื่อพนักงานขาย', 'ไม่พบข้อมูล')
            salesman_code = cust_info.get('พนักงานขาย', 'ไม่พบข้อมูล')
            default_unit = str(cust_info.get('หน่วย', 'box')).lower().strip()

            # แสดงผลข้อมูลสรุป
            col1, col2, col3 = st.columns(3)
            with col1:
                st.info(f"**พนักงานขาย:**\n\n{salesman_name} ({salesman_code})")
            with col2:
                st.success(f"**หน่วย Default จากลูกค้า:**\n\n{default_unit.upper()}")
            with col3:
                # กำหนด Pattern หน่วยที่จะใช้ค้นหา (เช่น Carton/ หรือ Box/)
                target_pattern = f"{default_unit.capitalize()}/"
                st.warning(f"**หน่วยที่ต้องใช้ใน S-018:**\n\n{target_pattern}xxx")

            st.markdown("---")

            # --- 3. การ Map สินค้าตามหน่วยที่กำหนด ---
            st.subheader(f"📦 2. รายการสินค้าที่ใช้หน่วย {target_pattern}")
            
            # กรองสินค้าใน PD_pack โดยค้นหาหน่วยที่มี Pattern ตรงกัน 
            if 'หน่วย' in products_df.columns:
                matched_products = products_df[
                    products_df['หน่วย'].str.contains(target_pattern, na=False, case=False)
                ]

                if not matched_products.empty:
                    st.dataframe(
                        matched_products[['สินค้า', 'ชื่อสินค้า', 'หน่วย', 'อัตราส่วน/หน่วยหลัก']], 
                        use_container_width=True
                    )
                    st.caption(f"พบสินค้าทั้งหมด {len(matched_products)} รายการ ที่รองรับหน่วย {target_pattern}")
                else:
                    st.error(f"❌ ไม่พบสินค้าที่ใช้หน่วย '{target_pattern}' ในไฟล์ PD_pack")
            else:
                st.error("❌ ไม่พบคอลัมน์ 'หน่วย' ในไฟล์ PD_pack")

        else:
            st.error("❌ ไม่พบคอลัมน์ 'รหัสลูกค้า' ในไฟล์ Cus_SaleList")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")

else:
    st.info("💡 กรุณาอัปโหลดไฟล์ Master Data ทั้งสองไฟล์ที่แถบด้านซ้ายเพื่อเริ่มระบบ")
    st.image("https://img.icons8.com/clouds/200/000000/upload.png")
