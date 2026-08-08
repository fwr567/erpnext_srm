app_name = "erpnext_srm_portal"
app_title = "ERPNext SRM Portal"
app_publisher = "fwr567"
app_description = "SRM Portal for ERPNext v16 - supplier portal, ASN, label/serial management"
app_icon = "octicon octicon-briefcase"
app_color = "grey"
app_email = "you@example.com"
app_license = "MIT"

# include web templates, JS, CSS
app_include_js = "/assets/erpnext_srm_portal/js/portal.js"

# expose these functions to site (website user will call via AJAX)
whitelisted_methods = [
    "erpnext_srm_portal.api.asn.submit_asn",
    "erpnext_srm_portal.api.asn.submit_asn_and_create_purchase_receipt",
    "erpnext_srm_portal.labels.generate.request_label_print",
]
