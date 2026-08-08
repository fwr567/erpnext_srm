# Patch: create a basic Workflow for Supplier ASN
import frappe

def execute():
    """Create Workflow for Supplier ASN if not exists."""
    try:
        if frappe.db.exists("Workflow", "Supplier ASN Workflow"):
            return
        wf = frappe.get_doc({
            "doctype": "Workflow",
            "workflow_name": "Supplier ASN Workflow",
            "document_type": "Supplier ASN",
            "is_active": 1,
            "workflow_state_field": "status",
            "states": [
                {"state": "Draft", "on_create": 1, "allow_edit": "Supplier, System Manager"},
                {"state": "Submitted", "allow_edit": "System Manager"},
                {"state": "Approved", "allow_edit": "System Manager"},
                {"state": "Rejected", "allow_edit": "System Manager"}
            ],
            "transitions": [
                {"state": "Draft", "action": "Submit", "next_state": "Submitted", "allowed": "Supplier"},
                {"state": "Submitted", "action": "Approve", "next_state": "Approved", "allowed": "System Manager"},
                {"state": "Submitted", "action": "Reject", "next_state": "Rejected", "allowed": "System Manager"}
            ]
        })
        wf.insert()
        frappe.db.commit()
        frappe.log_error(message="Supplier ASN Workflow created", title="erpnext_srm_portal.patch")
    except Exception as e:
        frappe.log_error(message=str(e), title="erpnext_srm_portal.patch.create_supplier_asn_workflow")
