# Patch: create unique index on Serial Pool (serial, item_code)
import frappe

def execute():
    """Add unique index to prevent duplicate serials for same item."""
    try:
        # Note: `tabSerial Pool` is the table name for the DocType Serial Pool
        frappe.db.sql("ALTER TABLE `tabSerial Pool` ADD UNIQUE KEY `idx_serial_item` (`serial`, `item_code`)")
        frappe.db.commit()
        frappe.log_error(message="Unique index idx_serial_item created on tabSerial Pool", title="erpnext_srm_portal.patch")
    except Exception as e:
        # If index exists or DB doesn't allow, log and continue
        frappe.log_error(message=str(e), title="erpnext_srm_portal.patch.create_unique_serial_index")
