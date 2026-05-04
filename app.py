import streamlit as st
import pandas as pd
import re
import io

st.set_page_config(page_title="Universal PO Parser", layout="wide")

st.title("🚀 ระบบแปลง PO PDF → S-018 (Universal Logic)")
st.markdown("---")

# --- 1. ส่วนการจัดการไฟล์ Master Data (XLSX) ---
st.sidebar.header("📁 1. Master Data")
uploaded_cust = st.sidebar.file_uploader("อัปโหลดไฟล์ Cus_SaleList.xlsx", type=['xlsx'])
uploaded_prod = st.sidebar.file_uploader("อัปโหลดไฟล์ PD_pack.xlsx", type=['xlsx'])

# --- 2. ส่วนการรับไฟล์ PO (PDF) ---
st.sidebar.header("📄 2. Customer PO")
uploaded_po = st.sidebar.file_uploader("อัปโหลด PO จากลูกค้า (PDF)", type=['pdf'])

if uploaded_cust and uploaded_prod:
    try:
        # อ่านไฟล์ Master Data
        customers_df = pd.read_excel(uploaded_cust)
        products_df = pd.read_excel(uploaded_prod)
        
        # ทำความสะอาดชื่อคอลัมน์
        customers_df.columns = customers_df.columns.str.strip()
        products_df.columns = products_df.columns.str.strip()

        # --- 3. Logic การตรวจจับลูกค้าอัตโนมัติ (Auto-detect Customer) ---
        # จำลองการสกัดเลข PO จาก PDF (ในระบบจริงจะใช้ pdfplumber หรือ AI)
        po_number_from_pdf = st.text_input("เลขที่ PO (ตรวจพบจากไฟล์):", "881.83423505")
        
        detected_cust = None
        for _, row in customers_df.iterrows():
            pattern = str(row['เลขที่ P/O ลูกค้า'])
            if pattern != 'nan' and re.search(pattern, po_number_from_pdf):
                detected_cust = row
                break
        
        if detected_cust is not None:
            cust_code = detected_cust['รหัสลูกค้า']
            cust_name = detected_cust['ชื่อลูกค้า']
            salesman_code = detected_cust['พนักงานขาย']
            default_unit = str(detected_cust['หน่วย']).lower().strip()
            
            # กำหนดคอลัมน์รหัสสินค้าเฉพาะ (MAK/TUS/TFS) จาก Suffix รหัสลูกค้า
            cust_type = cust_code.split('-')[-1] # เช่น 'MAK', 'TUS' หรือ 'TFS'
            
            st.success(f"✅ ตรวจพบลูกค้า: {cust_name} ({cust_code})")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("พนักงานขาย", salesman_code)
            col2.metric("หน่วยราคา Default", default_unit.upper())
            col3.metric("ค้นหารหัสสินค้าในช่อง", cust_type)

            st.markdown("---")

            # --- 4. การกรองหน่วยคู่ขนาน (Parallel Unit Filtering) ---
            # กรองสินค้าที่มีรหัสเฉพาะของลูกค้านั้น และมีหน่วย Carton/ หรือ Box/ ตาม Default
            unit_pattern = f"{default_unit.capitalize()}/"
            
            if cust_type in products_df.columns:
                valid_products = products_df[
                    (products_df[cust_type].notna()) & 
                    (products_df['หน่วย'].str.contains(unit_pattern, na=False))
                ]
                
                st.subheader(f"📦 รายการสินค้าที่ระบุรหัส {cust_type} (หน่วย {unit_pattern}xxx)")
                st.dataframe(valid_products[['สินค้า', 'ชื่อสินค้า', 'หน่วย', 'อัตราส่วน/หน่วยหลัก', cust_type]], use_container_width=True)

                # --- 5. S-018 Preparation (Mapping Logic) ---
                if uploaded_po:
                    st.subheader("🔍 ผลการเทียบรหัสสินค้าเพื่อสร้าง S-018")
                    
                    # จำลองข้อมูลที่สกัดจาก PDF (รหัสสินค้าลูกค้า, จำนวนสั่ง)
                    # ข้อมูลนี้จะถูกนำไป Match กับคอลัมน์ cust_type (MAK/TUS/TFS)
                    mock_extracted_items = [
                        {"sku": "812387", "qty": 10}, 
                        {"sku": "909837", "qty": 5}
                    ]
                    
                    s018_output = []
                    for item in mock_extracted_items:
                        # เทียบรหัสสินค้าลูกค้า เพื่อหา รหัสสินค้า GMT
                        match = valid_products[valid_products[cust_type].astype(str) == str(item['sku'])]
                        
                        if not match.empty:
                            target = match.iloc[0]
                            s018_output.append({
                                "เลขที่สั่งขาย": "", # รัน Prefix ในขั้นตอนถัดไป
                                "เลขที่ P/O ลูกค้า": po_number_from_pdf,
                                "ลูกค้า": cust_code,
                                "พนักงานขาย": salesman_code,
                                "สินค้า": target['สินค้า'], # รหัส GMT
                                "หน่วย": target['หน่วย'],
                                "จำนวนสั่ง-สินค้า": item['qty'], # คำนวณ Ratio หากจำเป็น
                                "หน่วยราคา": target['หน่วย'],
                                "จำนวนสั่ง (ราคา)": item['qty']
                            })
                    
                    if s018_output:
                        df_final = pd.DataFrame(s018_output)
                        st.table(df_final)
                        
                        # Export to CSV (UTF-8 BOM สำหรับ Excel ภาษาไทย)
                        csv_buffer = io.StringIO()
                        df_final.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
                        st.download_button("📥 Download S-018 CSV", data=csv_buffer.getvalue(), file_name=f"S018_{po_number_from_pdf}.csv", mime="text/csv")
            else:
                st.error(f"❌ ไม่พบช่องข้อมูลรหัสสินค้า '{cust_type}' ในไฟล์ Master Product")
        else:
            st.warning("⚠️ ไม่สามารถระบุลูกค้าได้จากเลขที่ PO นี้ กรุณาตรวจสอบ Pattern ใน Cus_SaleList")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผล: {e}")
else:
    st.info("💡 กรุณาอัปโหลดไฟล์ Master Data (XLSX) ทั้งสองไฟล์เพื่อเริ่มระบบ")
