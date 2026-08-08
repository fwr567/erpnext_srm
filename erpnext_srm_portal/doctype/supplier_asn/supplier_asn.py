from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class SupplierASN(Document):
    def validate(self):
        # Ensure every item line has serials or batch info before submit
        for row in self.items:
            # Allow drafts without serials
            if self.docstatus == 0:
                continue
            if not getattr(row, "serials", None) or not any([s.strip() for s in (row.serials or "").splitlines()]):
                frappe.throw(_("第 {0} 行缺少序列/批次，无法提交").format(row.idx))

    def before_submit(self):
        # At submit time, ensure serials exist for all lines
        for row in self.items:
            if not getattr(row, "serials", None) or not any([s.strip() for s in (row.serials or "").splitlines()]):
                frappe.throw(_("第 {0} 行缺少序列/批次，无法提交").format(row.idx))

    def on_submit(self):
        # mark status
        try:
            self.db_set('status', 'Submitted')
        except Exception:
            pass

    def on_update(self):
        # If status changed to Approved and no linked PR exists, create PR
        try:
            if getattr(self, 'status', '') == 'Approved' and not getattr(self, 'linked_purchase_receipt', None):
                # Use the API function to create PR
                from erpnext_srm_portal.api.asn import submit_asn_and_create_purchase_receipt
                try:
                    pr_name = submit_asn_and_create_purchase_receipt(self.name)
                    # already set in API
                except Exception as e:
                    # Log error but don't block
                    frappe.log_error(message=str(e), title='Supplier ASN auto PR creation failed')
        except Exception as e:
            frappe.log_error(message=str(e), title='Supplier ASN on_update error')
