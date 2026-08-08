import frappe
from frappe import _


def send_overprint_notification(overprint_name):
    """Send notification (email + ToDo) to configured approvers when Overprint Request (or Return Request) is created.
    Looks for approvers in site_config under srm.approvers (list of emails). If not set, falls back to System Manager users.
    Creates a ToDo for each approver so it appears in Desk as an actionable item.
    """
    try:
        site_conf = frappe.get_site_config() if hasattr(frappe, 'get_site_config') else {}
        approvers = []
        if site_conf and site_conf.get('srm') and site_conf.get('srm').get('approvers'):
            approvers = site_conf.get('srm').get('approvers')
        if not approvers:
            users = frappe.get_all('Has Role', filters={'role':'System Manager'}, fields=['parent'])
            approvers = []
            for u in users:
                try:
                    email = frappe.get_value('User', u.get('parent'), 'email')
                    if email:
                        approvers.append(email)
                except Exception:
                    continue
        if not approvers:
            frappe.log_error(message=f'No approvers found for notification {overprint_name}', title='overprint.notify')
            return False

        # Load the document (could be Overprint Request or Return Request)
        try:
            doc = frappe.get_doc('Overprint Request', overprint_name)
            title = f"Overprint Request: {doc.name}"
            body = f"An overprint request has been created.\n\nSupplier: {doc.supplier}\nPO: {doc.po_reference}\nItem: {doc.item_code}\nRequested Qty: {doc.requested_qty}\nReason: {doc.reason}\n\nPlease review and approve in Desk: {frappe.utils.get_url('/desk#Form/Overprint Request/' + doc.name)}"
        except Exception:
            try:
                doc = frappe.get_doc('Return Request', overprint_name)
                title = f"Return Request: {doc.name}"
                body = f"A return request has been created.\n\nSupplier: {doc.supplier}\nLinked PO/PR: {doc.linked_purchase_order or doc.linked_purchase_receipt}\nReason: {doc.reason}\n\nPlease review and process in Desk: {frappe.utils.get_url('/desk#Form/Return Request/' + doc.name)}"
            except Exception as e:
                frappe.log_error(message=str(e), title='overprint.notify.load_doc_failed')
                return False

        # send email
        try:
            frappe.sendmail(recipients=approvers, subject=title, message=body)
        except Exception as e:
            frappe.log_error(message=str(e), title='overprint.notify.sendmail_failed')

        # create ToDo for each approver to show in Desk
        for email in approvers:
            try:
                todo = frappe.get_doc({
                    'doctype': 'ToDo',
                    'description': body,
                    'assigned_to': email,
                    'reference_type': doc.doctype,
                    'reference_name': doc.name
                })
                todo.insert(ignore_permissions=True)
            except Exception as e:
                # If ToDo creation fails, log but continue
                frappe.log_error(message=str(e), title='overprint.notify.todo_failed')

        return True
    except Exception as e:
        frappe.log_error(message=str(e), title='overprint.notify.exception')
        return False
