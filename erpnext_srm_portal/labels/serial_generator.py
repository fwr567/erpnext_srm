import frappe
import hashlib
import time
from frappe import _


def _hash_lock_key(s):
    return hashlib.md5(s.encode()).hexdigest()


def _acquire_db_lock(lock_key, timeout=10):
    """Use MySQL GET_LOCK to acquire a named lock. Returns True if acquired."""
    try:
        res = frappe.db.sql("SELECT GET_LOCK(%s, %s)", (lock_key, timeout))
        if res and res[0] and res[0][0] == 1:
            return True
    except Exception as e:
        frappe.log_error(message=str(e), title='serial_generator.get_lock')
    return False


def _release_db_lock(lock_key):
    try:
        frappe.db.sql("SELECT RELEASE_LOCK(%s)", (lock_key,))
    except Exception as e:
        frappe.log_error(message=str(e), title='serial_generator.release_lock')


def generate_serials_db_lock(supplier, item_code, qty):
    """Generate serials using a DB-backed counter with GET_LOCK protection. Returns list of serials.
    Requires patch that creates table `tabSerial Counter` with columns (supplier, item_code, counter).
    """
    lock_name = _hash_lock_key(f"serial_gen:{supplier}:{item_code}")
    if not _acquire_db_lock(lock_name, timeout=10):
        frappe.throw(_('Unable to acquire DB lock for serial generation, try again'))
    try:
        # Ensure counter row exists
        row = frappe.db.sql("SELECT `counter` FROM `tabSerial Counter` WHERE supplier=%s AND item_code=%s", (supplier, item_code))
        if row:
            counter = int(row[0][0] or 0)
        else:
            # insert initial row
            frappe.db.sql("INSERT INTO `tabSerial Counter` (`supplier`, `item_code`, `counter`) VALUES (%s, %s, %s)", (supplier, item_code, 0))
            counter = 0
        serials = []
        for i in range(qty):
            counter += 1
            serial = f"SRM-{supplier[:6].upper()}-{item_code[:6].upper()}-{counter:08d}"
            # attempt to insert into Serial Pool
            try:
                frappe.get_doc({
                    'doctype': 'Serial Pool',
                    'serial': serial,
                    'item_code': item_code,
                    'status': 'reserved',
                    'reserved_for': None,
                    'created_by': frappe.session.user if hasattr(frappe, 'session') else 'system'
                }).insert(ignore_permissions=True)
                serials.append(serial)
            except Exception as e:
                # if duplicate due to race, try next counter value
                frappe.log_error(message=str(e), title='serial_generator.insert_serial_collision')
                # decrement i by not appending and continue loop to get extra serial
                # ensure we don't loop infinitely: just continue
                continue
        # update counter in table
        frappe.db.sql("UPDATE `tabSerial Counter` SET `counter`=%s WHERE supplier=%s AND item_code=%s", (counter, supplier, item_code))
        frappe.db.commit()
        return serials
    finally:
        _release_db_lock(lock_name)


def generate_serials_redis(supplier, item_code, qty):
    """Fallback redis-based generator using a namespaced counter (requires redis available)."""
    try:
        cache = frappe.cache()
        key = f"erpnext_srm:serial_counter:{supplier}:{item_code}"
        serials = []
        for i in range(qty):
            counter = cache.incr(key)
            serial = f"SRM-{supplier[:6].upper()}-{item_code[:6].upper()}-{counter:08d}"
            # try insert into Serial Pool
            try:
                frappe.get_doc({
                    'doctype': 'Serial Pool',
                    'serial': serial,
                    'item_code': item_code,
                    'status': 'reserved',
                    'reserved_for': None,
                    'created_by': frappe.session.user if hasattr(frappe, 'session') else 'system'
                }).insert(ignore_permissions=True)
                serials.append(serial)
            except Exception as e:
                frappe.log_error(message=str(e), title='serial_generator.redis_insert_collision')
                # try next
                continue
        frappe.db.commit()
        return serials
    except Exception as e:
        frappe.log_error(message=str(e), title='serial_generator.redis_error')
        return []


def generate_serials_fallback(supplier, item_code, qty):
    """Last-resort generator using timestamp+random with retries. Less safe under heavy concurrency."""
    import random, time
    serials = []
    attempts = 0
    max_attempts = qty * 10
    while len(serials) < qty and attempts < max_attempts:
        ts = int(time.time() * 1000)
        suf = random.randint(1000, 9999)
        serial = f"SRM-{supplier[:6].upper()}-{item_code[:6].upper()}-{ts}-{suf}"
        try:
            frappe.get_doc({
                'doctype': 'Serial Pool',
                'serial': serial,
                'item_code': item_code,
                'status': 'reserved',
                'reserved_for': None,
                'created_by': frappe.session.user if hasattr(frappe, 'session') else 'system'
            }).insert(ignore_permissions=True)
            serials.append(serial)
            frappe.db.commit()
        except Exception as e:
            attempts += 1
            continue
    if len(serials) < qty:
        frappe.throw(_('Unable to generate required unique serials'))
    return serials


def generate_serials_robust(supplier, item_code, qty):
    """High-level function: try DB lock counter -> Redis counter -> fallback timestamp random generation."""
    # try DB lock first
    try:
        serials = generate_serials_db_lock(supplier, item_code, qty)
        if serials and len(serials) >= qty:
            return serials
    except Exception as e:
        frappe.log_error(message=str(e), title='serial_generator.db_lock_fail')
    # try redis
    try:
        serials = generate_serials_redis(supplier, item_code, qty)
        if serials and len(serials) >= qty:
            return serials
    except Exception as e:
        frappe.log_error(message=str(e), title='serial_generator.redis_fail')
    # fallback
    return generate_serials_fallback(supplier, item_code, qty)
