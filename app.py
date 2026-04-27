import streamlit as st
import pandas as pd
import io
import re

# --- CONFIG ---
st.set_page_config(page_title="PO to S-018", layout="wide")

if 'db_pd' not in st.session_state: st.session_state.db_pd = None
if 'db_cus' not in st.session_state: st.session_state.db_cus = None

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Master Data (Overwrite)")
    up_pd = st.file_uploader("Upload PD_pack.xlsx", type=["xlsx"])
    if up_pd:
        st.session_state.db_pd = pd.read_excel(up_pd)
        st.success("อัปเดตสินค้าเรียบร้อย")
        
    up_cus = st.file_uploader("Upload Cus_SaleList.xlsx", type=["xlsx"])
    if up_cus:
        st.session_state.db_cus = pd.read_excel(up_cus)
        st.success("อัปเดตลูกค้าเรียบร้อย")

# --- MAIN APP ---
st.title("📦 ระบบแปลง PO (S-018 Generator)")

if st.session_state.db_pd is None or st.session_state.db_cus is None:
    st.warning("⚠️ กรุณาอัปโหลด Master Data ทั้ง 2 ไฟล์ก่อนนะคะ")
else:
    # STEP 1: เลือกพนักงานและลูกค้า
    cus_df = st.session_state.db_cus.copy()
    cus_df['Cus_Label'] = cus_df['รหัสลูกค้า'].astype(str) + " | " + cus_df['ชื่อลูกค้า'].astype(str)
    selected_cus = st.selectbox("เลือกรหัสหรือชื่อลูกค้า", cus_df['Cus_Label'].unique())
    
    # ดึงข้อมูล Master ลูกค้า
    cus_code = selected_cus.split(" | ")[0]
    cus_info = cus_df[cus_df['รหัสลูกค้า'] == cus_code].iloc[0]
    target_unit_price = str(cus_info['หน่วย']).strip() # หน่วยราคาจาก Master ลูกค้า

    # STEP 2: อัปโหลด PO
    st.divider()
    po_file = st.file_uploader("อัปโหลดไฟล์ PO (PDF/Excel/Image)", type=["pdf", "xlsx", "png", "jpg"])

    if po_file:
        st.info("กำลังประมวลผลข้อมูล...")
        
        # --- [Logic: PO Detection & Mapping] ---
        # จำลองข้อมูลที่ได้จากการ Parse (ในแอปจริงส่วนนี้จะรับค่าจาก Gemini)
        raw_po_no = "881.9999" # ตัวอย่างเลขที่ PO
        raw_items = [
            {"id": "8906371", "qty": 10}, # รหัสลูกค้า/Barcode
            {"id": "8859497306117", "qty": 5}
        ]

        # 1. ตรวจสอบเลขที่ PO ตามเงื่อนไข
        clean_po = "ไม่ระบุ"
        if "881." in raw_po_no: clean_po = raw_po_no # Makro
        elif re.match(r"^4\d{7}$", raw_po_no): clean_po = raw_po_no # Lotus (8 หลัก ขึ้นต้นด้วย 4)
        elif re.match(r"^T\d{9}$", raw_po_no): clean_po = raw_po_no # TFS (T + 9 หลัก)

        # 2. ค้นหาและคำนวณสินค้า
        parsed_results = []
        pd_master = st.session_state.db_pd

        for i, item in enumerate(raw_items):
            # ค้นหาสินค้า (Method 1: Customer Code, Method 2: Barcode)
            match = pd_master[
                (pd_master['Mak'].astype(str) == item['id']) | 
                (pd_master['Tus'].astype(str) == item['id']) | 
                (pd_master['Tfs'].astype(str) == item['id']) |
                (pd_master['Barcode'].astype(str) == item['id'])
            ]

            if not match.empty:
                prod_code = match.iloc[0]['สินค้า']
                prod_name = match.iloc[0]['ชื่อสินค้า']
                
                # ดึง Ratio ของ "หน่วยราคา" (จาก Cus_SaleList)
                row_price = match[match['หน่วย'].str.contains(target_unit_price, case=False, na=False)]
                ratio_price = row_price.iloc[0]['อัตราส่วน/หน่วยหลัก'] if not row_price.empty else 1
                
                # ดึง Ratio ของ "หน่วย Box"
                row_box = pd_master[(pd_master['สินค้า'] == prod_code) & (pd_master['หน่วย'].str.contains('Box', case=False, na=False))]
                
                if not row_box.empty:
                    ratio_box = row_box.iloc[0]['อัตราส่วน/หน่วยหลัก']
                    unit_box_name = row_box.iloc[0]['หน่วย']
                    # คำนวณ จำนวนสั่ง-สินค้า (Box)
                    calc_qty_box = (item['qty'] * ratio_price) / ratio_box
                else:
                    # ถ้าไม่เจอหน่วย Box ให้ใช้หน่วยเดิม
                    ratio_box = ratio_price
                    unit_box_name = target_unit_price
                    calc_qty_box = item['qty']

                parsed_results.append({
                    "สินค้า S-018": prod_code,
                    "ชื่อสินค้า": prod_name,
                    "หน่วยราคา": f"{target_unit_price} (แปลงเป็น {unit_box_name})",
                    "จำนวนสั่ง ราคา": item['qty'],
                    "คำนวณ": calc_qty_box,
                    "สถานะ": "✅ พร้อม"
                })
            else:
                parsed_results.append({
                    "สินค้า S-018": item['id'],
                    "ชื่อสินค้า": "❌ ไม่พบใน Master",
                    "หน่วยราคา": "-",
                    "จำนวนสั่ง ราคา": item['qty'],
                    "คำนวณ": 0,
                    "สถานะ": "⚠️ แก้ไข"
                })

        # STEP 3: หน้า Review (เหลือ 4 คอลัมน์หลัก + Action)
        st.subheader(f"📝 Review Data (PO: {clean_po})")
        review_df = pd.DataFrame(parsed_results)
        
        # แสดงตารางให้พี่นุ่นตรวจสอบ/แก้ไข
        edited_df = st.data_editor(
            review_df,
            column_order=("สินค้า S-018", "ชื่อสินค้า", "หน่วยราคา", "จำนวนสั่ง ราคา", "สถานะ"),
            disabled=["ชื่อสินค้า", "สถานะ"],
            num_rows="dynamic"
        )

        # STEP 4: Export
        if st.button("🚀 ยืนยันและสร้างไฟล์ S-018"):
            st.success("กำลังสร้างไฟล์ S-018 และส่งข้อมูลเข้า ERP...")
            # ส่วนนี้ใส่ Logic การสร้างไฟล์ Excel และปุ่มดาวน์โหลดได้เลยค่ะ
