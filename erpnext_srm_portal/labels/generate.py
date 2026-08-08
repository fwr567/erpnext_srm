import frappe
from frappe import _
from erpnext_srm_portal.approvals.utils import is_user_approver

@frappe.whitelist()
def approve_overprint(overprint_name, approve=True):
    """Approve or reject an Overprint Request. If approved, generate the labels and create Label Print Request.
    Approver must be configured approver or System Manager fallback.
    """
    user = frappe.session.user if hasattr(frappe, 'session') else None
    if not is_user_approver(user):
        frappe.throw(_('Only approvers can approve overprint requests'))
    orq = frappe.get_doc('Overprint Request', overprint_name)
    if approve:
        # generate serials (use robust generator to be safe)
        qty = int(orq.requested_qty)
        try:
            from erpnext_srm_portal.labels.serial_generator import generate_serials_robust
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
            'created_by': user
        }).insert(ignore_permissions=True)
        orq.status = 'Approved'
        orq.approved_by = user
        orq.linked_label_print_request = lpr.name
        orq.save(ignore_permissions=True)
        frappe.db.commit()
        return {'status':'approved','label_print_request': lpr.name}
    else:
        orq.status = 'Rejected'
        orq.approved_by = user
        orq.save(ignore_permissions=True)
        frappe.db.commit()
        return {'status':'rejected'}
