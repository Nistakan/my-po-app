import pandas as pd
import re

# 1. โหลดข้อมูลจากไฟล์ Master (CSV/Excel)
# อ้างอิงโครงสร้างจากไฟล์ที่อัปโหลด [cite: 1, 7]
customers_df = pd.read_csv('Cus_SaleList.xlsx - Sheet.csv')
products_df = pd.read_csv('PD_pack.xlsx - Sheet.csv')

def get_customer_info(customer_code):
    """ ค้นหาข้อมูลลูกค้า พนักงานขาย และหน่วย Default [cite: 1] """
    cust_data = customers_df[customers_df['รหัสลูกค้า'] == customer_code].iloc[0]
    return {
        "customer_name": cust_data['ชื่อลูกค้า'],
        "salesman_code": cust_data['พนักงานขาย'],
        "salesman_name": cust_data['ชื่อพนักงานขาย'],
        "default_unit": cust_data['หน่วย']  # เช่น 'carton' หรือ 'box'
    }

def find_product_unit_row(gmt_code, unit_type):
    """ 
    ค้นหา Row สินค้าตามหน่วยที่กำหนด (Carton หรือ Box) 
    เพื่อดึงหน่วยเต็ม (Unit String) และ Ratio 
    """
    # กรองสินค้าตามรหัส GMT 
    product_rows = products_df[products_df['สินค้า'] == gmt_code]
    
    # กำหนด Keyword สำหรับค้นหาหน่วย 
    # ถ้า unit_type == 'carton' ให้หาแถวที่มีคำว่า 'Carton/'
    # ถ้า unit_type == 'box' ให้หาแถวที่มีคำว่า 'Box/'
    search_key = unit_type.capitalize() + '/'
    
    unit_row = product_rows[product_rows['หน่วย'].str.contains(search_key, na=False)]
    
    if not unit_row.empty:
        return {
            "full_unit": unit_row.iloc[0]['หน่วย'],              # เช่น 'Carton/168' 
            "ratio": float(unit_row.iloc[0]['อัตราส่วน/หน่วยหลัก'])  # เช่น 168.0 
        }
    return None

def process_po_to_s018(customer_code, po_items):
    """ แปลงรายการจาก PO เป็นรูปแบบ S-018 """
    # 1. ดึงข้อมูลลูกค้าและหน่วยตั้งต้น [cite: 1]
    cust_info = get_customer_info(customer_code)
    target_unit_type = cust_info['default_unit']  # 'carton' หรือ 'box'
    
    s018_results = []
    
    for item in po_items:
        gmt_code = item['gmt_code']
        po_qty = item['po_qty']
        
        # 2. ค้นหาข้อมูลหน่วยและ Ratio จาก MasterProduct 
        unit_info = find_product_unit_row(gmt_code, target_unit_type)
        
        if unit_info:
            # คำนวณตาม Logic: 
            # จำนวนสั่ง-ราคา (price_qty) = จำนวนดิบจาก PO
            # หน่วยราคา (unit_price) = หน่วยที่ Map ได้ (Carton/xxx)
            s018_item = {
                "ลูกค้า": customer_code,
                "พนักงานขาย": cust_info['salesman_code'],
                "สินค้า": gmt_code,
                "หน่วยราคา (unit_price)": unit_info['full_unit'],
                "จำนวนสั่ง (ราคา)": po_qty,
                "อัตราส่วน (Ratio)": unit_info['ratio'],
                "จำนวนสั่ง-สินค้า (qty)": po_qty # กรณีสั่งหน่วยเดียวกับหน่วยราคา
            }
            s018_results.append(s018_item)
            
    return pd.DataFrame(s018_results)

# --- ตัวอย่างการใช้งาน ---
# สมมติเรา Parse PO มาได้รายการสินค้า GMT Code ดังนี้:
example_po_items = [
    {"gmt_code": "FSMT1001", "po_qty": 10},
    {"gmt_code": "FSMT2201", "po_qty": 5}
]

# เลือกลูกค้าที่เป็นหน่วย Carton (เช่น MT-TUS) [cite: 5]
output_df = process_po_to_s018("MT-TUS", example_po_items)

print("--- ผลลัพธ์สำหรับ Export S-018 ---")
print(output_df[['สินค้า', 'หน่วยราคา (unit_price)', 'จำนวนสั่ง (ราคา)', 'อัตราส่วน (Ratio)']])
