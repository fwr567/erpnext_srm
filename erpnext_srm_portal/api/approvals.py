import frappe
from frappe import _
from erpnext_srm_portal.approvals.utils import is_user_approver

@frappe.whitelist()
def get_pending_requests():
    """Return pending Overprint Requests and Return Requests for approvers to review."""
    # Only logged in users can call; further filtering by role can be applied in UI
    user = frappe.session.user if hasattr(frappe, 'session') else None
    if not is_user_approver(user):
        frappe.throw(_('Only approvers can view pending requests'))
    overprints = frappe.get_all('Overprint Request', filters={'status':'Requested'}, fields=['name','supplier','item_code','requested_qty','reason'], order_by='creation desc')
    returns = frappe.get_all('Return Request', filters={'status':'Requested'}, fields=['name','supplier','linked_purchase_order','linked_purchase_receipt','reason'], order_by='creation desc')
    return {'overprint': overprints, 'returns': returns}

@frappe.whitelist()
def approve_request(doctype, name, approve=True):
    """Generic approver endpoint to approve or reject Overprint / Return requests.
    Caller must be an approver as configured in site_config.srm.approvers or site_config.srm.approver_roles, or be System Manager if none configured.
    """
    user = frappe.session.user if hasattr(frappe, 'session') else None
    if not is_user_approver(user):
        frappe.throw(_('Only approvers can approve requests'))
    if doctype == 'Overprint Request':
        from erpnext_srm_portal.labels.generate import approve_overprint
        return approve_overprint(name, approve=approve)
    elif doctype == 'Return Request':
        from erpnext_srm_portal.api.returns import approve_return_request
        return approve_return_request(name, approve=approve)
    else:
        frappe.throw(_('Unsupported request type'))
