import frappe
from frappe import _

@frappe.whitelist()
def get_pending_requests():
    """Return pending Overprint Requests and Return Requests for approvers to review."""
    # Only logged in users can call; further filtering by role can be applied in UI
    overprints = frappe.get_all('Overprint Request', filters={'status':'Requested'}, fields=['name','supplier','item_code','requested_qty','reason'], order_by='creation desc')
    returns = frappe.get_all('Return Request', filters={'status':'Requested'}, fields=['name','supplier','linked_purchase_order','linked_purchase_receipt','reason'], order_by='creation desc')
    return {'overprint': overprints, 'returns': returns}

@frappe.whitelist()
def approve_request(doctype, name, approve=True):
    """Generic approver endpoint to approve or reject Overprint / Return requests.
    Caller must have System Manager role (or this can be relaxed/configured).
    """
    if not frappe.has_role('System Manager'):
        frappe.throw(_('Only System Manager can approve requests'))
    if doctype == 'Overprint Request':
        from erpnext_srm_portal.labels.generate import approve_overprint
        return approve_overprint(name, approve=approve)
    elif doctype == 'Return Request':
        from erpnext_srm_portal.api.returns import approve_return_request
        return approve_return_request(name, approve=approve)
    else:
        frappe.throw(_('Unsupported request type'))
