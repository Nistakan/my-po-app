import streamlit as st
import pandas as pd
import re
import io

# การตั้งค่าหน้าจอ Streamlit
st.set_page_config(page_title="Universal PO to S-018 Converter", layout="wide")

st.title("🚀 ระบบแปลง PO PDF → S-018 (Full Automation)")
st.markdown("---")

# --- 1. การจัดการไฟล์ Master Data (xlsx) ---
st.sidebar.header("📁 1. Master Data (XLSX)")
uploaded_cust = st.sidebar.file_uploader("อัปโหลด Cus_SaleList.xlsx", type=['xlsx'])
uploaded_prod = st.sidebar.file_uploader("อัปโหลด PD_pack.xlsx", type=['xlsx'])

# --- 2. การรับไฟล์ PO (PDF) ---
st.sidebar.header("📄 2. Customer PO (PDF)")
uploaded_po = st.sidebar.file_uploader("อัปโหลดใบสั่งซื้อจากลูกค้า", type=['pdf'])

# ฟังก์ชันสำหรับสร้างไฟล์ S-018 (.xlsx) ตามโครงสร้างมาตรฐาน
def create_s018_xlsx(data_list):
    output = io.BytesIO()
    # รายชื่อคอลัมน์มาตรฐานของระบบ S-018
    columns_s018 = [
        "เลขที่สั่งขาย", "วันที่สั่งขาย", "ยืนยัน", "ลูกค้า", "ประเภทใบสั่งขาย", 
        "พนักงานขาย", "แผนก", "เลขที่ P/O ลูกค้า", "วันที่ P/O ลูกค้า", 
        "วันที่ต้องการ", "ประเภทเอกสาร", "ประเภทความต้องการ", "Def.แผนกเบิก", 
        "หมายเหตุ", "ลำดับ-สินค้า", "สินค้า", "หน่วย", "จำนวนสั่ง-สินค้า", 
        "หน่วยราคา", "จำนวนสั่ง (ราคา)", "ราคาขาย", "%ส่วนลด", "%ส่วนลด2", 
        "ส่วนลด/หน่วย", "%ส่วนลดพิเศษ", "ของแถม", "หมายเหตุ-สินค้า"
    ]
    
    final_df = pd.DataFrame(data_list)
    # เติมคอลัมน์ที่ขาดให้ครบตาม Format
    for col in columns_s018:
        if col not in final_df.columns:
            final_df[col] = ""
            
    final_df = final_df[columns_s018] # จัดเรียงลำดับคอลัมน์
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        final_df.to_excel(writer, index=False, sheet_name='S-018_Import')
    return output.getvalue()

if uploaded_cust and uploaded_prod:
    try:
        # โหลดข้อมูล Master Data 
        customers_df = pd.read_excel(uploaded_cust)
        products_df = pd.read_excel(uploaded_prod)
        
        # ทำความสะอาดชื่อคอลัมน์
        customers_df.columns = customers_df.columns.str.strip()
        products_df.columns = products_df.columns.str.strip()

        if uploaded_po:
            # --- 3. Auto-detect Customer จาก Regex ใน Cus_SaleList ---
            # [Simulation] สมมติข้อความที่สกัดได้จาก PDF (ในงานจริงใช้ pdfplumber หรือ Gemini API)
            # ตัวอย่างข้อความที่มีเลข PO ของ Makro: "เลขที่ใบสั่งซื้อ 881.83423505"
            extracted_text_from_pdf = "Purchase Order No: 881.83423505 Date: 2026-05-04" 
            
            detected_cust = None
            po_no_found = ""
            
            for _, row in customers_df.iterrows():
                # ดึง Regex Pattern จากคอลัมน์ "เลขที่ P/O ลูกค้า" 
                pattern = str(row['เลขที่ P/O ลูกค้า'])
                if pattern != 'nan':
                    match = re.search(pattern, extracted_text_from_pdf)
                    if match:
                        detected_cust = row
                        po_no_found = match.group(0) # ดึงเลข PO ที่ตรงกับ Pattern
                        break
            
            if detected_cust is not None:
                cust_code = detected_cust['รหัสลูกค้า'] [cite: 1]
                salesman_code = detected_cust['พนักงานขาย'] [cite: 1]
                salesman_name = detected_cust['ชื่อพนักงานขาย'] [cite: 1]
                default_unit = str(detected_cust['หน่วย']).lower().strip() [cite: 1]
                
                # Dynamic Column Selection: เลือก MAK, TUS หรือ TFS ตามรหัสลูกค้า 
                cust_type_col = cust_code.split('-')[-1] # เช่น MT-MAK -> MAK
                
                st.success(f"✅ ตรวจพบลูกค้าอัตโนมัติ: {detected_cust['ชื่อลูกค้า']} ({cust_code})")
                st.info(f"🔢 เลขที่ PO ที่พบ: {po_no_found}")

                # --- 4. Mapping สินค้า & S-018 Preparation ---
                # [Simulation] รายการสินค้าและจำนวนที่สกัดได้จาก PDF
                # สกัดรหัสสินค้าเฉพาะลูกค้าเพื่อมา Match กับ PD_pack 
                mock_po_items = [
                    {"sku_from_pdf": "812387", "qty": 10}, # รหัส MAK ของ FSMT1001 [cite: 17]
                    {"sku_from_pdf": "909837", "qty": 5}    # รหัส MAK ของ FSMT100X01 
                ]
                
                s018_data_list = []
                # กำหนด Pattern หน่วยให้ตรงกับ Default ของลูกค้า (เช่น Carton/ หรือ Box/)
                unit_pattern = f"{default_unit.capitalize()}/"
                
                for item in mock_po_items:
                    # ค้นหารหัสสินค้า GMT จากคอลัมน์เฉพาะ (MAK/TUS/TFS) พร้อมกรองหน่วย 
                    match = products_df[
                        (products_df[cust_type_col].astype(str) == str(item['sku_from_pdf'])) &
                        (products_df['หน่วย'].str.contains(unit_pattern, na=False))
                    ]
                    
                    if not match.empty:
                        target = match.iloc[0]
                        s018_data_list.append({
                            "ลูกค้า": cust_code,
                            "พนักงานขาย": salesman_code,
                            "เลขที่ P/O ลูกค้า": po_no_found,
                            "สินค้า": target['สินค้า'], # รหัส GMT
                            "หน่วย": target['หน่วย'],
                            "จำนวนสั่ง-สินค้า": item['qty'],
                            "หน่วยราคา": target['หน่วย'],
                            "จำนวนสั่ง (ราคา)": item['qty'],
                            "ของแถม": "N|No",
                            "ยืนยัน": "N|สร้างใหม่",
                            "ประเภทเอกสาร": "ขายโมเดิร์นเทรด"
                        })
                
                if s018_data_list:
                    st.subheader("📊 ตารางตรวจสอบข้อมูล S-018")
                    df_preview = pd.DataFrame(s018_data_list)
                    st.dataframe(df_preview, use_container_width=True)
                    
                    # สร้างไฟล์ Excel สำหรับดาวน์โหลด
                    xlsx_file = create_s018_xlsx(s018_data_list)
                    st.download_button(
                        label="📥 Download S-018 (.xlsx)",
                        data=xlsx_file,
                        file_name=f"S018_{cust_code}_{po_no_found}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.error(f"❌ ไม่พบรหัสสินค้าในคอลัมน์ {cust_type_col} ที่ตรงกับข้อมูลใน PO")
            else:
                st.warning("⚠️ เลข PO ใน PDF ไม่ตรงกับ Pattern ของลูกค้ารายใดในระบบ")
        else:
            st.info("💡 กรุณาอัปโหลดใบสั่งซื้อ (PDF) เพื่อเริ่มการตรวจสอบ")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผล: {e}")
else:
    st.info("💡 กรุณาอัปโหลดไฟล์ Master Data ทั้งสองไฟล์ (Cus_SaleList และ PD_pack) ในรูปแบบ .xlsx")
