import frappe
from frappe import _

@frappe.whitelist()
def map_user_to_supplier(user=None, supplier=None):
    """Map a portal user (email or id) to a Supplier. Only System Manager or the user themselves can create mapping.

    Usage: call as logged-in user. If user not provided, use frappe.session.user
    """
    if not user:
        user = frappe.session.user
    if not supplier:
        frappe.throw(_("supplier is required"))
    # Only allow mapping if current user is System Manager or same user
    if frappe.session.user != user and not frappe.has_role('System Manager'):
        frappe.throw(_("Only System Manager can map other users"))
    # create or update mapping
    doc = frappe.get_doc({
        'doctype': 'Supplier Portal User Mapping',
        'user': user,
        'supplier': supplier
    })
    doc.insert(ignore_permissions=True)
    return doc.name
