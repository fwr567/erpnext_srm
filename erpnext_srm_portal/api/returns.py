import frappe
from frappe import _
from erpnext_srm_portal.approvals.utils import is_user_approver

@frappe.whitelist()
def approve_return_request(return_name, approve=True):
    """System Manager or configured approver approves or rejects a Return Request. If approved, mark serials in Serial Pool as 'returned'."""
    user = frappe.session.user if hasattr(frappe, 'session') else None
    if not is_user_approver(user):
        frappe.throw(_('Only approvers can approve return requests'))
    rr = frappe.get_doc('Return Request', return_name)
    if approve:
        rr.status = 'Approved'
        rr.approved_by = user
        rr.save()
        # mark serials as returned in Serial Pool
        for row in rr.items:
            if row.serials:
                for s in [x.strip() for x in (row.serials or '').splitlines() if x.strip()]:
                    try:
                        sp = frappe.db.get_value('Serial Pool', {'serial': s}, 'name')
                        if sp:
                            sp_doc = frappe.get_doc('Serial Pool', sp)
                            sp_doc.status = 'returned'
                            sp_doc.db_set('status', 'returned')
                            sp_doc.db_set('reserved_for', rr.name)
                    except Exception as e:
                        frappe.log_error(message=str(e), title='approve_return_request.serial_update')
        frappe.db.commit()
        return {'status': 'approved'}
    else:
        rr.status = 'Rejected'
        rr.approved_by = user
        rr.save()
        frappe.db.commit()
        return {'status': 'rejected'}
