# Vendor Shipment Tracking (Odoo 19)

Native Odoo addon for managing inbound shipments from vendors to Pakistan.

## Features

- Unique shipment numbers such as `SHP/2026/00001`
- Vendor order number and one or more linked confirmed Purchase Orders
- Shipment ETD, ETA, status, origin, destination, transport mode, and tracking/B/L number
- Shipping-document ETD, ETA, receipt date, and status
- Email confirmation to the vendor, shipping company, or both using Odoo's editable email composer
- Separate Not Sent, Awaiting Confirmation, Confirmed, and Not Confirmed states
- Chatter history, activities, attachments, calendar view, filters, and groupings
- Purchase Order **Create Shipment** action and **Shipments** smart button
- User/Administrator access levels and multi-company record isolation

## Installation

1. Copy `vendor_shipment_tracking` into an Odoo 19 addons directory.
2. Add that directory to `addons_path` if needed and restart Odoo.
3. Update the Apps list, search for **Vendor Shipment Tracking**, and install it.
4. In Settings > Users, grant **Shipment Tracking / User** or **Administrator**.
5. Configure an outgoing email server before sending confirmation emails.

The recipient's reply is kept in the shipment chatter when inbound email routing is configured.
Use **Mark Confirmed** or **Mark Not Confirmed** to record the final response.
