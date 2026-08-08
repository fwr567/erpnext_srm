import frappe
from frappe import _
from erpnext_srm_portal.labels.serial_generator import generate_serials_robust
from erpnext_srm_portal.labels.serial_allocator import get_serials

@frappe.whitelist()
def request_label_print(supplier, item_code, qty=1, po_reference=None, reserve_mode='printed'):
    """Request label print. If po_reference provided and qty exceeds PO remaining, create an Overprint Request for approval."""
    # If PO provided, check remaining qty for the item
    if po_reference:
        try:
            po_items = frappe.get_all('Purchase Order Item', filters={'parent': po_reference, 'item_code': item_code}, fields=['name','qty','received_qty'])
            if po_items:
                po_item = po_items[0]
                ordered = float(po_item.get('qty') or 0)
                received = float(po_item.get('received_qty') or 0)
                remaining = ordered - received
            else:
                remaining = 0
        except Exception as e:
            frappe.log_error(message=str(e), title='request_label_print.po_check')
            remaining = 0
        # default allowed overprint threshold (could be made configurable)
        allowed_overprint = frappe.get_site_config().get('srm', {}).get('allowed_overprint_threshold', 0) if hasattr(frappe, 'get_site_config') else 0
        if float(qty) > remaining + float(allowed_overprint):
            # create Overprint Request and return pending
            req = frappe.get_doc({
                'doctype': 'Overprint Request',
                'supplier': supplier,
                'po_reference': po_reference,
                'item_code': item_code,
                'requested_qty': qty,
                'reason': f'Auto-generated overprint request: qty {qty} > remaining {remaining}',
                'status': 'Requested',
                'requested_by': frappe.session.user if hasattr(frappe, 'session') else 'system'
            }).insert(ignore_permissions=True)
            return {'status':'overprint_requested', 'overprint_request': req.name, 'remaining_qty': remaining}
    # else proceed with allocation/generation
    try:
        serials = get_serials(supplier, item_code, int(qty), block_size=200)
    except Exception:
        serials = generate_serials_robust(supplier, item_code, int(qty))
    lpr = frappe.get_doc({
        "doctype": "Label Print Request",
        "supplier": supplier,
        "item_code": item_code,
        "serials_assigned": "\n".join(serials),
        "print_count": 1,
        "created_by": frappe.session.user if hasattr(frappe, 'session') else 'system'
    }).insert(ignore_permissions=True)
    return {"status":"ok", "serials": serials, "print_record": lpr.name}

@frappe.whitelist()
def request_overprint(supplier, po_reference, item_code, requested_qty, reason=''):
    """Create an Overprint Request explicitly."""
    doc = frappe.get_doc({
        'doctype': 'Overprint Request',
        'supplier': supplier,
        'po_reference': po_reference,
        'item_code': item_code,
        'requested_qty': requested_qty,
        'reason': reason,
        'status': 'Requested',
        'requested_by': frappe.session.user if hasattr(frappe, 'session') else 'system'
    }).insert(ignore_permissions=True)
    return doc.name

@frappe.whitelist()
def approve_overprint(overprint_name, approve=True):
    """Approve or reject an Overprint Request. If approved, generate the labels and create Label Print Request.
    Only System Manager can approve.
    """
    if not frappe.has_role('System Manager'):
        frappe.throw(_('Only System Manager can approve overprint requests'))
    orq = frappe.get_doc('Overprint Request', overprint_name)
    if approve:
        # generate serials (use robust generator to be safe)
        qty = int(orq.requested_qty)
        try:
            serials = generate_serials_robust(orq.supplier, orq.item_code, qty)
        except Exception as e:
            frappe.log_error(message=str(e), title='approve_overprint.generate_failed')
            frappe.throw(_('Failed to generate serials for overprint: {0}').format(str(e)))
        lpr = frappe.get_doc({
            'doctype': 'Label Print Request',
            'supplier': orq.supplier,
            'item_code': orq.item_code,
            'serials_assigned': "\n".join(serials),
            'print_count': 1,
            'created_by': frappe.session.user
        }).insert(ignore_permissions=True)
        orq.status = 'Approved'
        orq.approved_by = frappe.session.user
        orq.linked_label_print_request = lpr.name
        orq.save(ignore_permissions=True)
        frappe.db.commit()
        return {'status':'approved','label_print_request': lpr.name}
    else:
        orq.status = 'Rejected'
        orq.approved_by = frappe.session.user
        orq.save(ignore_permissions=True)
        frappe.db.commit()
        return {'status':'rejected'}
