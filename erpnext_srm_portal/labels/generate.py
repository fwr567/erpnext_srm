import frappe, time, random
from frappe.utils import now_datetime

def _generate_serial(supplier, item_code):
    ts = int(time.time())
    suf = random.randint(1000,9999)
    return f"SRM-{supplier[:6].upper()}-{item_code[:6].upper()}-{ts}-{suf}"

@frappe.whitelist()
def request_label_print(supplier, item_code, qty=1):
    serials = []
    for i in range(int(qty)):
        s = _generate_serial(supplier, item_code)
        serials.append(s)
        # 创建 Serial Pool 记录
        frappe.get_doc({
            "doctype": "Serial Pool",
            "serial": s,
            "item_code": item_code,
            "status": "printed",
            "reserved_for": None,
            "created_by": frappe.session.user if hasattr(frappe, 'session') else 'system'
        }).insert(ignore_permissions=True)
    # 创建打印记录（Label Print Request）
    lpr = frappe.get_doc({
        "doctype": "Label Print Request",
        "supplier": supplier,
        "item_code": item_code,
        "serials_assigned": "\n".join(serials),
        "print_count": 1,
        "created_by": frappe.session.user if hasattr(frappe, 'session') else 'system'
    }).insert(ignore_permissions=True)
    return {"serials": serials, "print_record": lpr.name}
