import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="Universal PO Parser", layout="wide")

st.title("🚀 ระบบแปลง PO PDF → S-018 (Universal Logic)")
st.markdown("---")

# --- 1. โหลดไฟล์ Master Data ---
st.sidebar.header("📁 1. Master Data")
uploaded_cust = st.sidebar.file_uploader("Cus_SaleList.xlsx", type=['xlsx'])
uploaded_prod = st.sidebar.file_uploader("PD_pack.xlsx", type=['xlsx'])

# --- 2. อัปโหลด PO PDF ---
st.sidebar.header("📄 2. Customer PO")
uploaded_po = st.sidebar.file_uploader("Upload PO (PDF)", type=['pdf'])

if uploaded_cust and uploaded_prod:
    try:
        # อ่านไฟล์และจัดการชื่อคอลัมน์ 
        customers_df = pd.read_excel(uploaded_cust)
        products_df = pd.read_excel(uploaded_prod)
        customers_df.columns = customers_df.columns.str.strip()
        products_df.columns = products_df.columns.str.strip()

        # --- 3. Logic การตรวจจับลูกค้าอัตโนมัติ (Auto-detect Customer) ---
        # สมมติเลข PO ที่สกัดได้จาก PDF (ในระบบจริงจะใช้ pdfplumber/AI ดึงเลขนี้ออกมา)
        # ตัวอย่างเลข PO สำหรับทดสอบ: '881.83423505' (MAK) หรือ '435037492' (TUS)
        po_number_from_pdf = st.text_input("เลขที่ PO (ตรวจจับจาก PDF):", "881.83423505")
        
        detected_cust_row = None
        for index, row in customers_df.iterrows():
            pattern = str(row['เลขที่ P/O ลูกค้า'])
            if pattern and pattern != 'nan':
                # ใช้ Regex เทียบ Pattern จาก Cus_SaleList [cite: 3]
                if re.search(pattern, po_number_from_pdf):
                    detected_cust_row = row
                    break
        
        if detected_cust_row is not None:
            cust_code = detected_cust_row['รหัสลูกค้า'] [cite: 1]
            cust_name = detected_cust_row['ชื่อลูกค้า'] [cite: 1]
            salesman_code = detected_cust_row['พนักงานขาย'] [cite: 1]
            default_unit = str(detected_cust_row['หน่วย']).lower().strip() [cite: 1]
            
            # ระบุคอลัมน์รหัสสินค้าเฉพาะของลูกค้า (MAK/TUS/TFS) 
            cust_type_suffix = cust_code.split('-')[-1] # เช่น 'MAK', 'TUS', 'TFS'
            
            st.success(f"✅ ตรวจพบลูกค้า: {cust_name} ({cust_code})")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("พนักงานขาย", f"{salesman_code}")
            col2.metric("หน่วยตั้งต้น", default_unit.upper())
            col3.metric("คอลัมน์รหัสสินค้า", cust_type_suffix)

            st.markdown("---")

            # --- 4. การแสดงสินค้าที่รองรับ (Mapping View) ---
            st.subheader(f"📦 สินค้าที่ลงทะเบียนรหัส {cust_type_suffix}")
            
            # กรองสินค้าที่มีรหัสเฉพาะของลูกค้านี้ และหน่วยตรงตาม Default (เช่น Carton/xxx) [cite: 7, 8]
            unit_pattern = f"{default_unit.capitalize()}/"
            valid_products = products_df[
                (products_df[cust_type_suffix].notna()) & 
                (products_df['หน่วย'].str.contains(unit_pattern, na=False))
            ]
            
            st.dataframe(valid_products[['สินค้า', 'ชื่อสินค้า', 'หน่วย', 'อัตราส่วน/หน่วยหลัก', cust_type_suffix]], use_container_width=True)

            # --- 5. การจำลองการ Parse และเทียบรหัส (Matching Logic) ---
            if uploaded_po:
                st.subheader("🔍 ผลการสกัดข้อมูลและเทียบรหัส GMT")
                
                # ตัวอย่างข้อมูลที่อ่านได้จาก PDF (รหัสสินค้าลูกค้า, จำนวน)
                # ในขั้นตอนนี้ ระบบจะใช้รหัสจาก PDF มา Match กับคอลัมน์ MAK/TUS/TFS 
                mock_po_items = [
                    {"customer_sku": "812387", "qty": 50}, # ตัวอย่างรหัส MAK
                    {"customer_sku": "909837", "qty": 20}
                ]
                
                final_s018_data = []
                for item in mock_po_items:
                    # ค้นหารหัส GMT โดยใช้รหัสลูกค้าเทียบกับคอลัมน์ที่ระบุ 
                    match = valid_products[valid_products[cust_type_suffix].astype(str) == item['customer_sku']]
                    
                    if not match.empty:
                        target = match.iloc[0]
                        final_s018_data.append({
                            "เลขที่ PO": po_number_from_pdf,
                            "รหัสสินค้า (ลูกค้า)": item['customer_sku'],
                            "รหัสสินค้า (GMT)": target['สินค้า'],
                            "ชื่อสินค้า": target['ชื่อสินค้า'],
                            "จำนวนสั่ง": item['qty'],
                            "หน่วยราคา": target['หน่วย'],
                            "อัตราส่วน": target['อัตราส่วน/หน่วยหลัก']
                        })
                
                if final_s018_data:
                    st.table(pd.DataFrame(final_s018_data))
                    st.download_button("📥 Download Excel สำหรับ S-018", 
                                     data=pd.DataFrame(final_s018_data).to_csv(index=False).encode('utf-8-sig'),
                                     file_name=f"S018_{cust_code}_{po_number_from_pdf}.csv",
                                     mime="text/csv")
                else:
                    st.warning("⚠️ ไม่พบรหัสสินค้าใน PO ที่ตรงกับ Master Data ของลูกค้านี้")

        else:
            st.error("❌ ไม่สามารถระบุลูกค้าจากเลขที่ PO นี้ได้ กรุณาตรวจสอบ Pattern ใน Cus_SaleList")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")
else:
    st.info("💡 กรุณาอัปโหลดไฟล์ Master Data (XLSX) ทั้งสองไฟล์ที่แถบด้านซ้าย")
