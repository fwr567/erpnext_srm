# Next steps & notes

This commit adds server-side validation on Supplier ASN, an API to create ASN from the portal, a frontend helper and portal page, patches to add a unique index on Serial Pool and to create a basic Workflow for Supplier ASN.

After running `bench --site your-site migrate`, please check: 
- The patches should run and create the DB unique index and Workflow. If any DB engine restriction exists, the index creation may fail silently (check patch logs in Error Log).
- Adjust permissions for Website Users / Supplier role so they can create Supplier ASN via portal but cannot modify other sensitive objects.

Security note: `create_supplier_asn` uses `frappe.only_for('Website Manager')` for extra protection in this scaffold — adapt to your portal user mapping as needed.
