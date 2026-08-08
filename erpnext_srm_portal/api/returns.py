import frappe
from frappe import _
from erpnext_srm_portal.notifications.notify import send_overprint_notification

@frappe.whitelist()
def create_return_request(supplier, items=None, linked_purchase_receipt=None, linked_purchase_order=None, reason=''):
    """Supplier creates a Return Request. `items` is JSON string or list of dicts with item_code, qty, serials (optional list or newline string)."""
    import json
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except Exception:
            frappe.throw(_('Invalid items payload'))
    if not items or not isinstance(items, list):
        frappe.throw(_('Items payload required'))
    doc = frappe.get_doc({
        'doctype': 'Return Request',
        'supplier': supplier,
        'linked_purchase_receipt': linked_purchase_receipt,
        'linked_purchase_order': linked_purchase_order,
        'reason': reason,
        'status': 'Requested',
        'requested_by': frappe.session.user if hasattr(frappe, 'session') else 'system'
    })
    for it in items:
        row = doc.append('items', {})
        row.item_code = it.get('item_code')
        row.qty = it.get('qty') or 0
        serials = it.get('serials')
        if isinstance(serials, list):
            row.serials = '\n'.join(serials)
        else:
            row.serials = serials
    doc.insert()
    # send notification to approvers (reuse helper)
    try:
        send_overprint_notification(doc.name)
    except Exception:
        pass
    return doc.name

@frappe.whitelist()
def approve_return_request(return_name, approve=True):
    """System Manager approves or rejects a Return Request. If approved, mark serials in Serial Pool as 'returned' (or 'released') and set status to Approved.
    Actual stock/accounting entries are left to be created by warehouse/finance workflows (or a separate process), to avoid assumptions about warehouse naming.
    """
    if not frappe.has_role('System Manager'):
        frappe.throw(_('Only System Manager can approve return requests'))
    rr = frappe.get_doc('Return Request', return_name)
    if approve:
        rr.status = 'Approved'
        rr.approved_by = frappe.session.user
        rr.save()
        # mark serials as returned in Serial Pool
        for row in rr.items:
            if row.serials:
                for s in [x.strip() for x in (row.serials or '').splitlines() if x.strip()]:
                    try:
                        sp = frappe.get_doc('Serial Pool', {'serial': s}) if frappe.db.exists('Serial Pool', {'serial': s}) else None
                        if sp:
                            sp.status = 'returned'
                            sp.db_set('status', 'returned')
                            sp.db_set('reserved_for', rr.name)
                    except Exception as e:
                        frappe.log_error(message=str(e), title='approve_return_request.serial_update')
        frappe.db.commit()
        return {'status': 'approved'}
    else:
        rr.status = 'Rejected'
        rr.approved_by = frappe.session.user
        rr.save()
        frappe.db.commit()
        return {'status': 'rejected'}
