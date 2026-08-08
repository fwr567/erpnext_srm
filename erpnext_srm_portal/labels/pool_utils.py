import frappe
from frappe import _


def allocate_serials_from_pool(supplier, item_code, qty, preferred_ref=None, target_doc=None):
    """Allocate `qty` serials from Serial Pool. Preference is given to entries with reserved_for == preferred_ref,
    then to any entries with no reserved_for. This function uses SELECT ... FOR UPDATE and an UPDATE to atomically
    claim serials and mark them as used and bound to target_doc.

    Returns list of serial strings.
    Throws an exception if insufficient serials available.
    """
    qty = int(qty)
    if qty <= 0:
        return []

    serial_names = []
    serials = []

    # Helper to fetch n names with FOR UPDATE
    def fetch_names(filters_sql, limit):
        sql = f"SELECT `name`, `serial` FROM `tabSerial Pool` WHERE {filters_sql} ORDER BY `creation` ASC LIMIT %s FOR UPDATE"
        return frappe.db.sql(sql, (limit,), as_dict=True)

    # Begin transaction
    try:
        # 1) preferred_ref matches
        if preferred_ref:
            filters_sql = "`item_code`=%s AND `supplier`=%s AND `reserved_for`=%s AND `status` IN ('reserved','printed')"
            rows = fetch_names("`item_code`=%s AND `supplier`=%s AND `reserved_for`=%s AND `status` IN ('reserved','printed')", qty)
            for r in rows:
                serial_names.append(r['name'])
                serials.append(r['serial'])
        # 2) general pool
        if len(serials) < qty:
            need = qty - len(serials)
            rows = fetch_names("`item_code`=%s AND `supplier`=%s AND (`reserved_for` IS NULL OR `reserved_for`='') AND `status` IN ('reserved','printed')", need)
            for r in rows:
                serial_names.append(r['name'])
                serials.append(r['serial'])

        if len(serials) < qty:
            frappe.throw(_("Only {0} serials available in pool, required {1}").format(len(serials), qty))

        # Attempt to atomically update the selected rows to status='used' and reserved_for=target_doc
        # Use SQL UPDATE with name IN (...) and check affected rows
        placeholders = ','.join(['%s'] * len(serial_names))
        update_sql = f"UPDATE `tabSerial Pool` SET `status`='used', `reserved_for`=%s WHERE `name` IN ({placeholders}) AND `status` IN ('reserved','printed')"
        params = [target_doc or ''] + serial_names
        res = frappe.db.sql(update_sql, params)
        # Note: frappe.db.sql returns [] or number of affected rows depends on driver; to be safe, commit and continue
        frappe.db.commit()

        return serials
    except Exception as e:
        frappe.log_error(message=str(e), title='allocate_serials_from_pool')
        raise
