from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    shipment_ids = fields.Many2many(
        "vendor.shipment",
        "vendor_shipment_purchase_order_rel",
        "purchase_order_id",
        "shipment_id",
        string="Vendor Shipments",
        copy=False,
        groups="vendor_shipment_tracking.group_vendor_shipment_user",
    )
    shipment_count = fields.Integer(
        compute="_compute_shipment_count",
        groups="vendor_shipment_tracking.group_vendor_shipment_user",
    )

    @api.depends("shipment_ids")
    def _compute_shipment_count(self):
        for order in self:
            order.shipment_count = len(order.shipment_ids)

    def action_view_vendor_shipments(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "vendor_shipment_tracking.action_vendor_shipment"
        )
        action["domain"] = [("id", "in", self.shipment_ids.ids)]
        if self.shipment_count == 1:
            action["view_mode"] = "form"
            action["views"] = [(False, "form")]
            action["res_id"] = self.shipment_ids.id
        return action

    def action_create_vendor_shipment(self):
        self.ensure_one()
        if self.state not in ("purchase", "done"):
            raise UserError(_("Confirm the purchase order before creating its shipment."))
        return {
            "name": _("New Vendor Shipment"),
            "type": "ir.actions.act_window",
            "res_model": "vendor.shipment",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_vendor_id": self.partner_id.id,
                "default_vendor_order_number": self.partner_ref or self.name,
                "default_purchase_order_ids": [(6, 0, self.ids)],
                "default_company_id": self.company_id.id,
                "default_user_id": self.user_id.id or self.env.user.id,
            },
        }
