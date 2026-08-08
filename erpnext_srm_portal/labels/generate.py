import frappe
from frappe import _
from frappe.utils import now_datetime
import io
from PIL import Image
import qrcode


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


def _generate_serial(supplier, item_code):
    import time, random
    ts = int(time.time())
    suf = random.randint(1000,9999)
    return f"SRM-{supplier[:6].upper()}-{item_code[:6].upper()}-{ts}-{suf}"


@frappe.whitelist()
def generate_qr_png(serial_value):
    """Return binary image (PNG) for the serial's QR code. Caller can fetch via AJAX and render or download."""
    img = qrcode.make(serial_value)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    # Save as File and return file URL
    file_doc = frappe.get_doc({
        'doctype': 'File',
        'file_name': f'{serial_value}.png',
        'is_private': 1,
        'content': buf.getvalue()
    }).insert()
    return file_doc.file_url


@frappe.whitelist()
def generate_label_pdf(serial_values, supplier, item_code, template_name=None):
    """Generate a simple PDF with QR codes for given serial_values (list or newline string). Returns file URL."""
    if isinstance(serial_values, str):
        serial_values = [s.strip() for s in serial_values.splitlines() if s.strip()]
    imgs = []
    for s in serial_values:
        img = qrcode.make(s).convert('RGB')
        imgs.append(img)
    # Combine images into a single PDF
    buf = io.BytesIO()
    if imgs:
        imgs[0].save(buf, format='PDF', save_all=True, append_images=imgs[1:])
        buf.seek(0)
        file_doc = frappe.get_doc({
            'doctype': 'File',
            'file_name': f'label_{supplier}_{item_code}_{now_datetime().strftime("%Y%m%d%H%M%S")}.pdf',
            'is_private': 1,
            'content': buf.getvalue()
        }).insert()
        return file_doc.file_url
    else:
        frappe.throw(_('No serials provided'))


@frappe.whitelist()
def get_zpl_for_serial(serial_value, item_code, supplier, template_vars=None):
    """Return a ZPL string for a single label. Template_vars can override layout values."""
    # Simple ZPL template - user should adapt to printer width/height
    zpl = '^XA\n'
    zpl += '^FO50,50^A0N,30,30^FD{supplier}^FS\n'.format(supplier=supplier)
    zpl += '^FO50,90^A0N,30,30^FD{item}^FS\n'.format(item=item_code)
    zpl += '^FO50,130^BQN,2,5^FDQA,{serial}^FS\n'.format(serial=serial_value)
    zpl += '^FO200,130^A0N,30,30^FD{serial}^FS\n'.format(serial=serial_value)
    zpl += '^XZ'
    return zpl


@frappe.whitelist()
def request_reprint(label_print_request_name, reason):
    """Portal: request reprint of a label. Creates a Label Reprint Request doc."
    if not frappe.session.user:
        frappe.throw(_('Login required'))
    lpr = frappe.get_doc('Label Print Request', label_print_request_name)
    req = frappe.get_doc({
        'doctype': 'Label Reprint Request',
        'label_print_request': lpr.name,
        'reason': reason,
        'status': 'Requested',
        'requested_by': frappe.session.user
    }).insert()
    return req.name


@frappe.whitelist()
def approve_reprint(reprint_name, approve=True):
    """System Manager: approve or reject reprint. If approved, increments print_count and allows reprint."""
    if not frappe.has_role('System Manager'):
        frappe.throw(_('Only System Manager can approve reprints'))
    rr = frappe.get_doc('Label Reprint Request', reprint_name)
    lpr = frappe.get_doc('Label Print Request', rr.label_print_request)
    if approve:
        rr.status = 'Approved'
        rr.approved_by = frappe.session.user
        rr.save()
        # increment print count and record
        lpr.print_count = (lpr.print_count or 0) + 1
        lpr.save()
        return {'status': 'approved', 'print_count': lpr.print_count}
    else:
        rr.status = 'Rejected'
        rr.approved_by = frappe.session.user
        rr.save()
        return {'status': 'rejected'}
