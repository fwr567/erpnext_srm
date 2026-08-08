import frappe
from frappe import _
from erpnext_srm_portal.labels.serial_generator import generate_serials_robust
from frappe.utils import now_datetime
import io
from PIL import Image
import qrcode
import socket

@frappe.whitelist()
def request_label_print(supplier, item_code, qty=1, reserve_mode='printed'):
    serials = generate_serials_robust(supplier, item_code, int(qty))
    # create Serial Pool entries already done by generator
    # create Label Print Request
    lpr = frappe.get_doc({
        "doctype": "Label Print Request",
        "supplier": supplier,
        "item_code": item_code,
        "serials_assigned": "\n".join(serials),
        "print_count": 1,
        "created_by": frappe.session.user if hasattr(frappe, 'session') else 'system'
    }).insert(ignore_permissions=True)
    return {"serials": serials, "print_record": lpr.name}

# other functions unchanged (generate_qr_png, generate_label_pdf, get_zpl_for_serial, generate_zpl_batch, send_zpl_to_printer, request_reprint, approve_reprint)

def generate_qr_png(serial_value):
    img = qrcode.make(serial_value)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    file_doc = frappe.get_doc({
        'doctype': 'File',
        'file_name': f'{serial_value}.png',
        'is_private': 1,
        'content': buf.getvalue()
    }).insert()
    return file_doc.file_url


def generate_label_pdf(serial_values, supplier, item_code, template_name=None):
    if isinstance(serial_values, str):
        serial_values = [s.strip() for s in serial_values.splitlines() if s.strip()]
    imgs = []
    for s in serial_values:
        img = qrcode.make(s).convert('RGB')
        imgs.append(img)
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


def get_zpl_for_serial(serial_value, item_code, supplier, template_vars=None):
    def esc(v):
        return str(v).replace('^', '')
    zpl = '^XA\n'
    zpl += '^FO50,50^A0N,30,30^FD{supplier}^FS\n'.format(supplier=esc(supplier))
    zpl += '^FO50,90^A0N,30,30^FD{item}^FS\n'.format(item=esc(item_code))
    zpl += '^FO50,130^BQN,2,5^FDQA,{serial}^FS\n'.format(serial=esc(serial_value))
    zpl += '^FO200,130^A0N,30,30^FD{serial}^FS\n'.format(serial=esc(serial_value))
    zpl += '^XZ\n'
    return zpl


def generate_zpl_batch(serial_values, item_code, supplier, template_vars=None):
    if isinstance(serial_values, str):
        serial_values = [s.strip() for s in serial_values.splitlines() if s.strip()]
    parts = []
    for s in serial_values:
        parts.append(get_zpl_for_serial(s, item_code, supplier, template_vars))
    return '\n'.join(parts)


def send_zpl_to_printer(zpl_string, printer_ip, port=9100, timeout=5):
    if not printer_ip:
        frappe.throw(_('printer_ip required'))
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((printer_ip, int(port)))
        sock.sendall(zpl_string.encode('utf-8'))
        sock.close()
        return {'status': 'sent'}
    except Exception as e:
        frappe.log_error(message=str(e), title='ZPL send error')
        frappe.throw(_('Failed to send to printer: {0}').format(str(e)))


def request_reprint(label_print_request_name, reason):
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


def approve_reprint(reprint_name, approve=True):
    if not frappe.has_role('System Manager'):
        frappe.throw(_('Only System Manager can approve reprints'))
    rr = frappe.get_doc('Label Reprint Request', reprint_name)
    lpr = frappe.get_doc('Label Print Request', rr.label_print_request)
    if approve:
        rr.status = 'Approved'
        rr.approved_by = frappe.session.user
        rr.save()
        lpr.print_count = (lpr.print_count or 0) + 1
        lpr.save()
        return {'status': 'approved', 'print_count': lpr.print_count}
    else:
        rr.status = 'Rejected'
        rr.approved_by = frappe.session.user
        rr.save()
        return {'status': 'rejected'}
