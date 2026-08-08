from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class SupplierASN(Document):
    def validate(self):
        # Ensure every item line has serials or batch info before submit
        for row in self.items:
            # Only check when serials is required: we'll enforce on submit
            if self.docstatus == 0:
                # allow drafts without serials
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
