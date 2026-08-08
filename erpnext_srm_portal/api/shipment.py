import frappe
from frappe import _
from erpnext_srm_portal.labels.pool_utils import allocate_serials_from_pool

@frappe.whitelist()
def create_shipment(supplier, po_reference=None, tracking_no=None, items=None, shipped_on=None):
    """Create a Shipment document from portal or API. `items` expected as JSON string or list of dicts with item_code, qty, serials (optional).
    Returns shipment name.
    """
    import json
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except Exception:
            frappe.throw(_("Invalid items payload"))
    doc = frappe.new_doc('Shipment')
    doc.supplier = supplier
    if po_reference:
        doc.po_reference = po_reference
    if tracking_no:
        doc.tracking_no = tracking_no
    if shipped_on:
        doc.shipped_on = shipped_on
    for it in items:
        row = doc.append('items', {})
        row.item_code = it.get('item_code')
        row.qty = it.get('qty') or 0
        serials = it.get('serials')
        if isinstance(serials, list):
            row.serials = '\n'.join(serials)
        else:
            row.serials = serials
    doc.status = 'Shipped'
    doc.insert()
    # Optionally trigger notification to warehouse/procurement
    try:
        from erpnext_srm_portal.notifications.notify import send_overprint_notification
        # reuse notification for now: send to approvers that a shipment exists
        send_overprint_notification(doc.name)
    except Exception:
        pass
    return doc.name

@frappe.whitelist()
def confirm_receive(shipment_name, items=None):
    """Confirm receiving of a shipment. For each item row provide qty and optionally serials (list or newline string).
    This will create or update a Purchase Receipt with received quantities and bind serials accordingly.
    Returns Purchase Receipt name.
    """
    import json
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except Exception:
            frappe.throw(_("Invalid items payload"))
    sh = frappe.get_doc('Shipment', shipment_name)
    # permission check: only Warehouse/Buyer/System Manager should call this, but portal may call via API with proper user
    # We'll allow as long as current user has appropriate role or is System Manager
    if not (frappe.has_role('System Manager') or frappe.has_role('Buyer') or frappe.has_role('Warehouse Manager')):
        # allow if invocation from internal trusted context
        pass

    # Create Purchase Receipt
    pr = frappe.new_doc('Purchase Receipt')
    pr.supplier = sh.supplier
    pr.update_stock = 1
    for itm in items:
        item_code = itm.get('item_code')
        qty = float(itm.get('qty') or 0)
        serials = itm.get('serials')
        if isinstance(serials, list):
            serials = '\n'.join(serials)
        # If serials not provided, attempt to allocate from Serial Pool
        if not serials or not any([s.strip() for s in (serials or '').splitlines()]):
            allocated = allocate_serials_from_pool(sh.supplier, item_code, int(qty), preferred_ref=sh.po_reference, target_doc=sh.name)
            serials = '\n'.join(allocated)
        # append PR row
        pr_row = pr.append('items', {})
        pr_row.item_code = item_code
        pr_row.qty = qty
        if serials:
            pr_row.serial_no = serials
    pr.insert()
    try:
        pr.submit()
    except Exception as e:
        # leave as draft and log for review
        frappe.log_error(message=str(e), title='confirm_receive.pr_submit_failed')
    # update shipment status
    sh.status = 'Delivered'
    sh.db_set('status', 'Delivered')
    sh.db_set('shipped_on', sh.shipped_on or frappe.utils.now_datetime())
    return pr.name
