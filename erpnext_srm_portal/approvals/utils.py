import frappe


def _get_site_srm_config():
    try:
        conf = frappe.get_site_config()
        return conf.get('srm') if conf and isinstance(conf.get('srm'), dict) else {}
    except Exception:
        return {}


def _get_srm_settings_doc():
    try:
        # get_single will return the singleton doc if created; may raise if not installed
        return frappe.get_single('SRM Settings')
    except Exception:
        return None


def get_approver_emails():
    """Return list of approver emails from SRM Settings (Desk) -> site_config.srm.approvers -> derived from approver_roles.
    This prefers the SRM Settings single DocType when present to allow Desk management.
    """
    emails = []

    # 1) check SRM Settings singleton in Desk first
    settings = _get_srm_settings_doc()
    if settings:
        try:
            if getattr(settings, 'approvers', None):
                raw = getattr(settings, 'approvers') or ''
                # split by comma or newline
                parts = [p.strip() for p in raw.replace('\r','').replace('\n',',').split(',') if p.strip()]
                for p in parts:
                    if p and p not in emails:
                        emails.append(p)
            roles = getattr(settings, 'approver_roles', None)
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
            if emails:
                return emails
        except Exception:
            # fallthrough to site_config
            pass

    # 2) check site_config.srm
    srm = _get_site_srm_config()
    if srm:
        if srm.get('approvers') and isinstance(srm.get('approvers'), list):
            for e in srm.get('approvers'):
                if e and e not in emails:
                    emails.append(e)
        # roles in site_config
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
    # 3) fallback to System Manager users if still empty
    if not emails:
        users = frappe.get_all('Has Role', filters={'role':'System Manager'}, fields=['parent'])
        for u in users:
            try:
                email = frappe.get_value('User', u.get('parent'), 'email')
                if email and email not in emails:
                    emails.append(email)
            except Exception:
                continue
    return emails


def is_user_approver(user=None):
    """Return True if the given user is in approvers list or has one of approver_roles (from SRM Settings or site_config), or is System Manager when nothing configured."""
    if not user:
        try:
            user = frappe.session.user
        except Exception:
            user = None
    # 1) check SRM Settings
    settings = _get_srm_settings_doc()
    try:
        if settings:
            # check emails
            if getattr(settings, 'approvers', None):
                raw = getattr(settings, 'approvers') or ''
                parts = [p.strip() for p in raw.replace('\r','').replace('\n',',').split(',') if p.strip()]
                try:
                    user_email = frappe.get_value('User', user, 'email') or user
                except Exception:
                    user_email = user
                if user_email in parts:
                    return True
            # check roles
            approver_roles = getattr(settings, 'approver_roles', None)
            if approver_roles:
                if isinstance(approver_roles, str):
                    approver_roles = [r.strip() for r in approver_roles.split(',') if r.strip()]
                for role in approver_roles:
                    if frappe.has_role(role, user=user):
                        return True
            # if settings exist but no approvers configured, fallthrough to site_config
        # 2) check site_config
        srm = _get_site_srm_config()
        if srm:
            # emails
            if srm.get('approvers') and isinstance(srm.get('approvers'), list):
                try:
                    user_email = frappe.get_value('User', user, 'email') or user
                except Exception:
                    user_email = user
                if user_email in srm.get('approvers'):
                    return True
            # roles
            approver_roles = srm.get('approver_roles')
            if approver_roles:
                if isinstance(approver_roles, str):
                    approver_roles = [r.strip() for r in approver_roles.split(',') if r.strip()]
                for role in approver_roles:
                    if frappe.has_role(role, user=user):
                        return True
        # 3) fallback
        return frappe.has_role('System Manager', user=user)
    except Exception:
        return frappe.has_role('System Manager', user=user)
