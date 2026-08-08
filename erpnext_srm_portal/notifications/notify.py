import frappe
from frappe import _
from erpnext_srm_portal.approvals.utils import get_approver_emails


def send_overprint_notification(overprint_name):
    """Send notification (email + ToDo) to configured approvers when Overprint Request (or Return Request) is created.
    Looks for approvers in site_config under srm.approvers (list of emails) or srm.approver_roles; falls back to System Manager users.
    Creates a ToDo for each approver so it appears in Desk as an actionable item.
    Sends an HTML email with approve/reject links pointing to the portal approvals page.
    """
    try:
        approvers = get_approver_emails()
        if not approvers:
            frappe.log_error(message=f'No approvers found for notification {overprint_name}', title='overprint.notify')
            return False

        # Load the document (could be Overprint Request or Return Request)
        doc = None
        title = None
        body_text = None
        try:
            doc = frappe.get_doc('Overprint Request', overprint_name)
            title = f"Overprint Request: {doc.name}"
            body_text = f"An overprint request has been created.\n\nSupplier: {doc.supplier}\nPO: {doc.po_reference}\nItem: {doc.item_code}\nRequested Qty: {doc.requested_qty}\nReason: {doc.reason}\n\nPlease review and approve in Desk or via the portal approvals page." 
        except Exception:
            try:
                doc = frappe.get_doc('Return Request', overprint_name)
                title = f"Return Request: {doc.name}"
                body_text = f"A return request has been created.\n\nSupplier: {doc.supplier}\nLinked PO/PR: {doc.linked_purchase_order or doc.linked_purchase_receipt}\nReason: {doc.reason}\n\nPlease review and process in Desk or via the portal approvals page." 
            except Exception as e:
                frappe.log_error(message=str(e), title='overprint.notify.load_doc_failed')
                return False

        # Compose HTML message with links
        approvals_page = frappe.utils.get_url('/approval-portal')
        approve_link = f"{approvals_page}?doc={doc.doctype.replace(' ', '+')}|{doc.name}&action=approve"
        reject_link = f"{approvals_page}?doc={doc.doctype.replace(' ', '+')}|{doc.name}&action=reject"
        html_message = f"<p>{frappe.utils.escape_html(body_text).replace('\n','<br/>')}</p>"
        html_message += f"<p><a href=\"{approve_link}\">一键批准</a> &nbsp; <a href=\"{reject_link}\">一键拒绝</a></p>"

        # send email
        try:
            frappe.sendmail(recipients=approvers, subject=title, message=html_message, is_html=True)
        except Exception as e:
            frappe.log_error(message=str(e), title='overprint.notify.sendmail_failed')

        # create ToDo for each approver to show in Desk
        for email in approvers:
            try:
                todo = frappe.get_doc({
                    'doctype': 'ToDo',
                    'description': body_text,
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
