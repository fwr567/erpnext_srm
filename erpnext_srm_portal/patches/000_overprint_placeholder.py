# Patch: no DB changes required for Overprint Request DocType; placeholder patch for migration logging
import frappe

def execute():
    frappe.log_error(message='Overprint Request doctype added in app', title='erpnext_srm_portal.patch.overprint')
