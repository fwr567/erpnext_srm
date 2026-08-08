import frappe
from frappe import _


def send_overprint_notification(overprint_name):
    """Send notification (email) to configured approvers when Overprint Request is created.
    Looks for approvers in site_config under srm.approvers (list of emails). If not set, logs a warning.
    """
    try:
        site_conf = frappe.get_site_config() if hasattr(frappe, 'get_site_config') else {}
        approvers = []
        if site_conf and site_conf.get('srm') and site_conf.get('srm').get('approvers'):
            approvers = site_conf.get('srm').get('approvers')
        if not approvers:
            # try to fetch all System Manager users' emails
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
            frappe.log_error(message=f'No approvers found for overprint notification {overprint_name}', title='overprint.notify')
            return False
        overprint = frappe.get_doc('Overprint Request', overprint_name)
        subject = f"Overprint Request: {overprint.name} from {overprint.supplier}"
        message = f"An overprint request has been created.\n\nSupplier: {overprint.supplier}\nPO: {overprint.po_reference}\nItem: {overprint.item_code}\nRequested Qty: {overprint.requested_qty}\nReason: {overprint.reason}\n\nPlease review and approve in Desk: {frappe.utils.get_url('/desk#Form/Overprint Request/' + overprint.name)}"
        frappe.sendmail(recipients=approvers, subject=subject, message=message)
        return True
    except Exception as e:
        frappe.log_error(message=str(e), title='overprint.notify.exception')
        return False
