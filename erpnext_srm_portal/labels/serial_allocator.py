import frappe
import time
from frappe import _

# In-memory cache per process: { key: {'serials': [..], 'idx': 0} }
_allocator_cache = {}


def _key(supplier, item_code):
    return f"{supplier}::{item_code}"


def allocate_block_db(supplier, item_code, block_size=100):
    """Acquire DB lock and allocate a block of serial numbers by increasing the Serial Counter.
    Inserts corresponding entries into Serial Pool with status 'reserved' and returns list of serials.
    This function is safe under concurrent calls because it uses GET_LOCK.
    """
    lock_key = f"serial_alloc:{supplier}:{item_code}"
    try:
        # acquire lock with timeout
        res = frappe.db.sql("SELECT GET_LOCK(%s, %s)", (lock_key, 10))
        if not res or res[0][0] != 1:
            frappe.throw(_('Could not acquire lock for serial allocation'))
        # ensure counter row exists
        row = frappe.db.sql("SELECT `counter` FROM `tabSerial Counter` WHERE supplier=%s AND item_code=%s FOR UPDATE", (supplier, item_code))
        if row:
            counter = int(row[0][0] or 0)
            # update counter by block_size
            new_counter = counter + block_size
            frappe.db.sql("UPDATE `tabSerial Counter` SET `counter`=%s WHERE supplier=%s AND item_code=%s", (new_counter, supplier, item_code))
        else:
            # insert row and set counter = block_size
            counter = 0
            new_counter = block_size
            frappe.db.sql("INSERT INTO `tabSerial Counter` (`name`, `supplier`, `item_code`, `counter`) VALUES (%s, %s, %s, %s)", (frappe.generate_hash(length=8), supplier, item_code, new_counter))
        # generate serials for range (counter+1 .. new_counter)
        serials = []
        for i in range(counter + 1, new_counter + 1):
            serial = f"SRM-{supplier[:6].upper()}-{item_code[:6].upper()}-{i:08d}"
            serials.append(serial)
        # bulk insert into Serial Pool
        for s in serials:
            try:
                frappe.get_doc({
                    'doctype': 'Serial Pool',
                    'serial': s,
                    'item_code': item_code,
                    'status': 'reserved',
                    'reserved_for': None,
                    'created_by': frappe.session.user if hasattr(frappe, 'session') else 'system'
                }).insert(ignore_permissions=True)
            except Exception as e:
                # log and continue; duplicates should not occur because counter advanced under lock
                frappe.log_error(message=str(e), title='serial_allocator.insert_error')
        # commit changes
        frappe.db.commit()
        return serials
    finally:
        try:
            frappe.db.sql("SELECT RELEASE_LOCK(%s)", (lock_key,))
        except Exception:
            pass


def get_serials(supplier, item_code, qty, block_size=100):
    """Get `qty` serials using an in-memory block cache (per process). If cache exhausted, allocate a new block from DB.
    Returns list of serials.
    """
    key = _key(supplier, item_code)
    cache = _allocator_cache.get(key)
    if not cache or cache.get('idx', 0) >= len(cache.get('serials', [])):
        # allocate a new block
        size = max(block_size, qty)
        serials_block = allocate_block_db(supplier, item_code, size)
        _allocator_cache[key] = {'serials': serials_block, 'idx': 0}
        cache = _allocator_cache[key]
    # dispense
    start = cache['idx']
    end = start + qty
    serials_out = cache['serials'][start:end]
    cache['idx'] = end
    # if we didn't have enough in current block (shouldn't happen), allocate more recursively
    if len(serials_out) < qty:
        more = get_serials(supplier, item_code, qty - len(serials_out), block_size=block_size)
        serials_out.extend(more)
    return serials_out
