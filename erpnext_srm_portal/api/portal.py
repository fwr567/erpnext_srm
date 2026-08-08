import frappe
from frappe import _

@frappe.whitelist()
def create_supplier_asn(supplier, po_reference=None, items=None):
    """Create Supplier ASN document from portal. `items` expected as JSON string or list of dicts with keys: item_code, qty, uom (opt), serials (newline-separated string or list)."""
    frappe.only_for('Website Manager', perm_type='read')
    # allow website users but still check
    import json
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except Exception:
            frappe.throw(_("Invalid items payload"))
    if not items or not isinstance(items, list):
        frappe.throw(_("Items payload required"))
    doc = frappe.new_doc('Supplier ASN')
    doc.supplier = supplier
    if po_reference:
        doc.po_reference = po_reference
    for it in items:
        row = doc.append('items', {})
        row.item_code = it.get('item_code')
        row.qty = it.get('qty') or 0
        if it.get('uom'):
            row.uom = it.get('uom')
        serials = it.get('serials')
        if isinstance(serials, list):
            row.serials = '\n'.join(serials)
        else:
            row.serials = serials
    doc.insert()
    return doc.name
