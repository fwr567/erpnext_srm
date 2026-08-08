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

function tryAutoMapUser(successCb, errorCb) {
  frappe.call({
    method: 'erpnext_srm_portal.api.portal.map_user_to_supplier_auto',
    args: {},
    callback: function(r) {
      if(!r.exc) {
        successCb && successCb(r.message);
      } else {
        errorCb && errorCb(r.exc);
      }
    }
  });
}

function requestZplPrint(serials, item_code, supplier, printer_ip, successCb, errorCb) {
  // generate ZPL batch and send to printer
  frappe.call({
    method: 'erpnext_srm_portal.labels.generate.generate_zpl_batch',
    args: { serial_values: serials.join('\n'), item_code: item_code, supplier: supplier },
    callback: function(r) {
      if(!r.exc) {
        const zpl = r.message;
        frappe.call({
          method: 'erpnext_srm_portal.labels.generate.send_zpl_to_printer',
          args: { zpl_string: zpl, printer_ip: printer_ip },
          callback: function(r2) {
            if(!r2.exc) successCb && successCb(r2.message);
            else errorCb && errorCb(r2.exc);
          }
        });
      } else {
        errorCb && errorCb(r.exc);
      }
    }
  });
}

function createReturnRequest(payload, successCb, errorCb) {
  // payload: {supplier, items: [{item_code, qty, serials}], linked_purchase_receipt?, linked_purchase_order?, reason}
  frappe.call({
    method: 'erpnext_srm_portal.api.returns.create_return_request',
    args: payload,
    callback: function(r) {
      if(!r.exc) {
        successCb && successCb(r.message);
      } else {
        errorCb && errorCb(r.exc);
      }
    }
  });
}

function viewReturnRequestStatus(name, successCb, errorCb) {
  frappe.call({
    method: 'frappe.client.get',
    args: {doctype: 'Return Request', name: name},
    callback: function(r) {
      if(!r.exc) {
        successCb && successCb(r.message);
      } else {
        errorCb && errorCb(r.exc);
      }
    }
  });
}

function requestOverprint(payload, successCb, errorCb) {
  frappe.call({
    method: 'erpnext_srm_portal.labels.generate.request_overprint',
    args: payload,
    callback: function(r) {
      if(!r.exc) {
        successCb && successCb(r.message);
      } else {
        errorCb && errorCb(r.exc);
      }
    }
  });
}
