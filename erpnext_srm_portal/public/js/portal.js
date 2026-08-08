// portal frontend helper
function createSupplierASN(payload, successCb, errorCb) {
  // payload: {supplier, po_reference, items: [{item_code, qty, uom, serials}]}
  frappe.call({
    method: 'erpnext_srm_portal.api.portal.create_supplier_asn',
    args: payload,
    callback: function(r) {
      if(!r.exc) {
        // optionally submit
        const name = r.message;
        frappe.call({
          method: 'erpnext_srm_portal.api.asn.submit_asn',
          args: { asn_name: name },
          callback: function(r2) {
            if(!r2.exc) {
              successCb && successCb(r2.message);
            } else {
              errorCb && errorCb(r2.exc);
            }
          }
        });
      } else {
        errorCb && errorCb(r.exc);
      }
    }
  });
}
