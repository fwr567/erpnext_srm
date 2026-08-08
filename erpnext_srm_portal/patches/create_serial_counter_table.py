# Patch: create Serial Counter table for DB-backed sequential generation
import frappe

def execute():
    try:
        # Create table if not exists
        frappe.db.sql("""
            CREATE TABLE IF NOT EXISTS `tabSerial Counter` (
                `name` varchar(255) NOT NULL,
                `supplier` varchar(255) DEFAULT NULL,
                `item_code` varchar(255) DEFAULT NULL,
                `counter` bigint DEFAULT 0,
                PRIMARY KEY (`name`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        # Create unique key on supplier+item_code for lookup
        # We will manage counter update via GET_LOCK
        frappe.db.sql("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_serial_counter_supplier_item ON `tabSerial Counter` (supplier(100), item_code(100));
        """)
        frappe.db.commit()
        frappe.log_error(message='Serial Counter table ensured', title='erpnext_srm_portal.patch')
    except Exception as e:
        frappe.log_error(message=str(e), title='erpnext_srm_portal.patch.create_serial_counter')
