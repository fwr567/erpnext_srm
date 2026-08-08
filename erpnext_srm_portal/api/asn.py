import frappe
from frappe import _

@frappe.whitelist()
def submit_asn(asn_name):
    """Supplier 提交 ASN（由网站表单调用）"""
    asn = frappe.get_doc("Supplier ASN", asn_name)
    # 权限校验: 确保当前用户可以提交此 ASN
    if not asn.has_permission("write"):
        frappe.throw(_("没有权限提交此 ASN"))
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
    pr = frappe.new_doc("Purchase Receipt")
    pr.supplier = asn.supplier
    for row in asn.items:
        pr_row = pr.append("items", {})
        pr_row.item_code = row.item_code
        pr_row.qty = row.qty
        # ERPNext 接受 serial_no 为多行文本，按实际版本字段调整
        if getattr(row, "serials", None):
            pr_row.serial_no = "\n".join([s.strip() for s in row.serials.splitlines() if s.strip()])
    pr.insert()
    pr.submit()
    asn.db_set("linked_purchase_receipt", pr.name)
    return pr.name
