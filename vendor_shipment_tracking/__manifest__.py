{
    "name": "Vendor Shipment Tracking",
    "summary": "Track inbound vendor shipments and shipping documents",
    "version": "19.0.1.0.0",
    "category": "Inventory/Purchase",
    "author": "RA Traders",
    "license": "LGPL-3",
    "depends": ["mail", "purchase"],
    "data": [
        "security/vendor_shipment_security.xml",
        "security/ir.model.access.csv",
        "data/vendor_shipment_sequence.xml",
        "data/vendor_shipment_mail_template.xml",
        "views/vendor_shipment_views.xml",
        "views/purchase_order_views.xml",
    ],
    "application": True,
    "installable": True,
}
