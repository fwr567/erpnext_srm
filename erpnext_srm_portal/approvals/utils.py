import frappe


def _get_site_srm_config():
    try:
        conf = frappe.get_site_config()
        return conf.get('srm') if conf and isinstance(conf.get('srm'), dict) else {}
    except Exception:
        return {}


def get_approver_emails():
    """Return list of approver emails from site_config.srm.approvers or derived from approver_roles."""
    srm = _get_site_srm_config()
    emails = []
    if srm.get('approvers') and isinstance(srm.get('approvers'), list):
        emails = srm.get('approvers')
    # If approver_roles configured, lookup users with those roles
    roles = srm.get('approver_roles')
    if roles:
        if isinstance(roles, str):
            roles = [r.strip() for r in roles.split(',') if r.strip()]
        for role in roles:
            users = frappe.get_all('Has Role', filters={'role': role}, fields=['parent'])
            for u in users:
                try:
                    email = frappe.get_value('User', u.get('parent'), 'email')
                    if email and email not in emails:
                        emails.append(email)
                except Exception:
                    continue
    return emails


def is_user_approver(user=None):
    """Return True if the given user is in approvers list or has one of approver_roles, or is System Manager when nothing configured.
    """
    if not user:
        user = frappe.session.user if hasattr(frappe, 'session') else None
    # Superuser/super role
    try:
        # if explicit approvers list
        srm = _get_site_srm_config()
        approver_emails = srm.get('approvers') or []
        if approver_emails and user:
            # compare user email
            try:
                user_email = frappe.get_value('User', user, 'email') or user
            except Exception:
                user_email = user
            if user_email in approver_emails:
                return True
        # roles
        approver_roles = srm.get('approver_roles')
        if approver_roles:
            if isinstance(approver_roles, str):
                approver_roles = [r.strip() for r in approver_roles.split(',') if r.strip()]
            for role in approver_roles:
                if frappe.has_role(role, user=user):
                    return True
        # if nothing configured, fallback to System Manager check
        if not approver_emails and not approver_roles:
            return frappe.has_role('System Manager', user=user)
    except Exception:
        # safe fallback
        return frappe.has_role('System Manager', user=user)
    return False
