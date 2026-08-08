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


@frappe.whitelist()
def map_user_to_supplier_auto():
    """Try to automatically map the logged-in portal user to a Supplier based on email matching.
    Heuristics:
      1. If Supplier has a primary contact with this email -> map
      2. If Supplier has supplier_email field matching user email -> map
      3. If Supplier name or website contains user's email domain -> map (best-effort)
    Returns mapping name or None.
    """
    user = frappe.session.user
    if not user or user == 'Guest':
        return None
    user_email = None
    try:
        user_email = frappe.get_value('User', user, 'email') or user
    except Exception:
        user_email = user
    # 1. primary contact match
    contact = frappe.get_all('Contact', filters={'email_id': user_email}, fields=['name', 'supplier'])
    if contact:
        supplier = contact[0].get('supplier')
        if supplier:
            return map_user_to_supplier(user=user, supplier=supplier)
    # 2. supplier direct email field
    sup = frappe.get_all('Supplier', filters={'supplier_email': user_email}, fields=['name'])
    if sup:
        return map_user_to_supplier(user=user, supplier=sup[0].get('name'))
    # 3. domain heuristic
    if '@' in user_email:
        domain = user_email.split('@')[-1]
        sups = frappe.get_all('Supplier', filters=[['website', 'like', f'%{domain}%']], fields=['name'])
        if sups:
            return map_user_to_supplier(user=user, supplier=sups[0].get('name'))
    return None
