import frappe
from frappe import _

@frappe.whitelist()
def submit_asn(asn_name):
    """Supplier 提交 ASN（由网站表单调用）"""
    asn = frappe.get_doc("Supplier ASN", asn_name)
    # 权限校验: 确保当前用户可以提交此 ASN
    # Allow if user mapped to this supplier
    current = frappe.session.user
    mapping = frappe.get_all('Supplier Portal User Mapping', filters={'user': current, 'supplier': asn.supplier}, limit=1)
    if not mapping and not frappe.has_role('System Manager'):
        frappe.throw(_("当前用户未映射到该供应商，无法提交 ASN"))
    # 强校验：所有行必须有序列或批次
    for row in asn.items:
        if not getattr(row, "serials", None):
            frappe.throw(_("第 {0} 行缺少序列/批次，无法提交").format(row.idx))
    asn.status = "Submitted"
    asn.save()
    # 可触发工作流或通知
    return asn.name

@frappe.whitelist()
def submit_asn_and_create_purchase_receipt(asn_name):
    """审批通过后：把 ASN 转成 Purchase Receipt 并带入序列"""
    asn = frappe.get_doc("Supplier ASN", asn_name)
    if asn.status != "Approved":
        frappe.throw(_("只有 Approved 状态的 ASN 可以生成入库单"))
    # Idempotency: if already linked, return existing
    if getattr(asn, 'linked_purchase_receipt', None):
        return asn.linked_purchase_receipt
    pr = frappe.new_doc("Purchase Receipt")
    pr.supplier = asn.supplier
    pr.supplier_name = getattr(asn, 'supplier_name', None) or ''
    for row in asn.items:
        pr_row = pr.append("items", {})
        pr_row.item_code = row.item_code
        pr_row.qty = row.qty
        # ERPNext accepts serial_no as multi-line text
        if getattr(row, "serials", None):
            pr_row.serial_no = "\n".join([s.strip() for s in row.serials.splitlines() if s.strip()])
    pr.insert()
    try:
        pr.submit()
    except Exception as e:
        # If submit fails, leave PR as draft and log
        frappe.log_error(message=str(e), title='Purchase Receipt submit failed')
    asn.db_set("linked_purchase_receipt", pr.name)
    return pr.name
