from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class VendorShipment(models.Model):
    _name = "vendor.shipment"
    _description = "Vendor Shipment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "shipment_etd desc, id desc"

    name = fields.Char(
        string="Shipment No.",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        index="trigram",
        tracking=True,
    )
    active = fields.Boolean(default=True)
    vendor_id = fields.Many2one(
        "res.partner",
        string="Vendor",
        required=True,
        index=True,
        tracking=True,
        check_company=True,
    )
    vendor_order_number = fields.Char(
        string="Vendor Order Number",
        index="trigram",
        tracking=True,
        help="The vendor's order, proforma invoice, or booking reference.",
    )
    purchase_order_ids = fields.Many2many(
        "purchase.order",
        "vendor_shipment_purchase_order_rel",
        "shipment_id",
        "purchase_order_id",
        string="Purchase Orders",
        tracking=True,
    )
    purchase_order_count = fields.Integer(compute="_compute_purchase_order_count")

    shipping_company_id = fields.Many2one(
        "res.partner",
        string="Shipping Company",
        tracking=True,
        check_company=True,
    )
    transport_mode = fields.Selection(
        [
            ("sea", "Sea"),
            ("air", "Air"),
            ("road", "Road"),
            ("rail", "Rail"),
            ("courier", "Courier"),
        ],
        default="sea",
        required=True,
        tracking=True,
    )
    tracking_reference = fields.Char(string="Tracking / B/L Number", tracking=True)
    origin = fields.Char(string="Port / Place of Origin", tracking=True)
    destination = fields.Char(
        string="Port / Place of Destination",
        default=lambda self: _("Pakistan"),
        tracking=True,
    )

    shipment_etd = fields.Date(
        string="Shipment ETD",
        tracking=True,
        help="Estimated date of departure for the goods.",
    )
    shipment_eta = fields.Date(
        string="Shipment ETA",
        tracking=True,
        help="Estimated date of arrival for the goods.",
    )
    shipment_status = fields.Selection(
        [
            ("pending", "Pending"),
            ("booked", "Booked"),
            ("in_transit", "In Transit"),
            ("arrived", "Arrived"),
            ("delivered", "Delivered"),
            ("cancelled", "Cancelled"),
        ],
        string="Shipment Status",
        default="pending",
        required=True,
        index=True,
        tracking=True,
    )

    document_etd = fields.Date(
        string="Document ETD",
        tracking=True,
        help="Expected dispatch date for the original shipping documents.",
    )
    document_eta = fields.Date(
        string="Document ETA",
        tracking=True,
        help="Expected arrival date for the original shipping documents.",
    )
    document_status = fields.Selection(
        [
            ("not_received", "Not Received"),
            ("expected", "Expected"),
            ("received", "Received / With Us"),
        ],
        string="Document Status",
        default="not_received",
        required=True,
        index=True,
        tracking=True,
    )
    document_received_date = fields.Date(string="Documents Received On", tracking=True)

    send_confirmation_to = fields.Selection(
        [
            ("vendor", "Vendor"),
            ("shipping_company", "Shipping Company"),
            ("both", "Vendor and Shipping Company"),
        ],
        string="Send Confirmation To",
        default="vendor",
        required=True,
    )
    confirmation_recipient_ids = fields.Many2many(
        "res.partner",
        "vendor_shipment_computed_recipient_rel",
        "shipment_id",
        "partner_id",
        string="Confirmation Recipients",
        compute="_compute_confirmation_recipient_ids",
    )
    last_confirmation_recipient_ids = fields.Many2many(
        "res.partner",
        "vendor_shipment_last_recipient_rel",
        "shipment_id",
        "partner_id",
        string="Last Sent To",
        copy=False,
        readonly=True,
    )
    confirmation_status = fields.Selection(
        [
            ("draft", "Not Sent"),
            ("sent", "Awaiting Confirmation"),
            ("confirmed", "Confirmed"),
            ("not_confirmed", "Not Confirmed"),
        ],
        default="draft",
        required=True,
        copy=False,
        index=True,
        tracking=True,
    )
    confirmation_sent_date = fields.Datetime(
        string="Confirmation Sent On",
        copy=False,
        readonly=True,
        tracking=True,
    )
    confirmation_date = fields.Datetime(
        string="Response Recorded On",
        copy=False,
        readonly=True,
        tracking=True,
    )

    user_id = fields.Many2one(
        "res.users",
        string="Responsible",
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    notes = fields.Html()

    _shipment_date_order = models.Constraint(
        "CHECK(shipment_eta IS NULL OR shipment_etd IS NULL OR shipment_eta >= shipment_etd)",
        "Shipment ETA cannot be earlier than shipment ETD.",
    )
    _document_date_order = models.Constraint(
        "CHECK(document_eta IS NULL OR document_etd IS NULL OR document_eta >= document_etd)",
        "Document ETA cannot be earlier than document ETD.",
    )

    @api.depends("purchase_order_ids")
    def _compute_purchase_order_count(self):
        for shipment in self:
            shipment.purchase_order_count = len(shipment.purchase_order_ids)

    @api.depends("send_confirmation_to", "vendor_id", "shipping_company_id")
    def _compute_confirmation_recipient_ids(self):
        for shipment in self:
            recipients = self.env["res.partner"]
            if shipment.send_confirmation_to in ("vendor", "both"):
                recipients |= shipment.vendor_id
            if shipment.send_confirmation_to in ("shipping_company", "both"):
                recipients |= shipment.shipping_company_id
            shipment.confirmation_recipient_ids = recipients

    @api.onchange("purchase_order_ids")
    def _onchange_purchase_order_ids(self):
        if not self.purchase_order_ids:
            return
        vendors = self.purchase_order_ids.mapped("partner_id.commercial_partner_id")
        if len(vendors) == 1:
            self.vendor_id = vendors
        references = self.purchase_order_ids.mapped("partner_ref")
        if not self.vendor_order_number and references:
            self.vendor_order_number = ", ".join(dict.fromkeys(references))

    @api.onchange("document_status")
    def _onchange_document_status(self):
        if self.document_status == "received" and not self.document_received_date:
            self.document_received_date = fields.Date.context_today(self)

    @api.constrains("vendor_id", "purchase_order_ids", "company_id")
    def _check_purchase_orders(self):
        for shipment in self:
            wrong_vendor_orders = shipment.purchase_order_ids.filtered(
                lambda order: order.partner_id.commercial_partner_id
                != shipment.vendor_id.commercial_partner_id
            )
            if wrong_vendor_orders:
                raise ValidationError(
                    _(
                        "All purchase orders must belong to vendor %(vendor)s. Mismatched orders: %(orders)s",
                        vendor=shipment.vendor_id.display_name,
                        orders=", ".join(wrong_vendor_orders.mapped("name")),
                    )
                )
            wrong_company_orders = shipment.purchase_order_ids.filtered(
                lambda order: order.company_id != shipment.company_id
            )
            if wrong_company_orders:
                raise ValidationError(_("All purchase orders must belong to the shipment's company."))

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get("name", _("New")) == _("New"):
                values["name"] = self.env["ir.sequence"].next_by_code("vendor.shipment") or _("New")
        return super().create(vals_list)

    def copy(self, default=None):
        default = dict(default or {}, name=_("New"), confirmation_status="draft")
        return super().copy(default)

    def message_post(self, **kwargs):
        if self.env.context.get("mark_shipment_confirmation_as_sent"):
            values = {
                "confirmation_status": "sent",
                "confirmation_sent_date": fields.Datetime.now(),
                "confirmation_date": False,
            }
            recipient_ids = [
                partner_id
                for partner_id in (kwargs.get("partner_ids") or [])
                if isinstance(partner_id, int)
            ]
            if recipient_ids:
                values["last_confirmation_recipient_ids"] = [Command.set(recipient_ids)]
            # Tracking this write posts to the chatter. Remove the marker from
            # that nested post so a changed timestamp cannot recurse forever.
            self.with_context(mark_shipment_confirmation_as_sent=False).write(values)
        return super().message_post(**kwargs)

    def action_send_confirmation(self):
        self.ensure_one()
        if self.shipment_status == "cancelled":
            raise UserError(_("A cancelled shipment cannot be sent for confirmation."))

        recipients = self.confirmation_recipient_ids
        if not recipients:
            raise UserError(_("Select a vendor or shipping company before sending the email."))
        missing_email = recipients.filtered(lambda partner: not partner.email)
        if missing_email:
            raise UserError(
                _(
                    "Add an email address to these contacts before sending: %(contacts)s",
                    contacts=", ".join(missing_email.mapped("display_name")),
                )
            )

        template = self.env.ref("vendor_shipment_tracking.mail_template_shipment_confirmation")
        compose_view = self.env.ref("mail.email_compose_message_wizard_form")
        return {
            "name": _("Send Shipment Confirmation"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(compose_view.id, "form")],
            "view_id": compose_view.id,
            "target": "new",
            "context": {
                "default_model": self._name,
                "default_res_ids": self.ids,
                "default_template_id": template.id,
                "default_composition_mode": "comment",
                "default_email_layout_xmlid": "mail.mail_notification_layout_with_responsible_signature",
                "default_partner_ids": recipients.ids,
                "force_email": True,
                "hide_mail_template_management_options": True,
                "mark_shipment_confirmation_as_sent": True,
                "model_description": _("Vendor Shipment"),
            },
        }

    def action_mark_confirmed(self):
        for shipment in self:
            shipment.write(
                {
                    "confirmation_status": "confirmed",
                    "confirmation_date": fields.Datetime.now(),
                }
            )
            shipment.message_post(body=_("Shipment order marked as confirmed."))
        return True

    def action_mark_not_confirmed(self):
        for shipment in self:
            shipment.write(
                {
                    "confirmation_status": "not_confirmed",
                    "confirmation_date": fields.Datetime.now(),
                }
            )
            shipment.message_post(body=_("Shipment order marked as not confirmed."))
        return True

    def action_reset_confirmation(self):
        self.write(
            {
                "confirmation_status": "draft",
                "confirmation_sent_date": False,
                "confirmation_date": False,
                "last_confirmation_recipient_ids": [Command.clear()],
            }
        )
        return True

    def action_cancel(self):
        self.write({"shipment_status": "cancelled"})
        return True

    def action_reset_pending(self):
        self.write({"shipment_status": "pending"})
        return True

    def action_view_purchase_orders(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("purchase.purchase_form_action")
        action["domain"] = [("id", "in", self.purchase_order_ids.ids)]
        if self.purchase_order_count == 1:
            action["view_mode"] = "form"
            action["views"] = [(False, "form")]
            action["res_id"] = self.purchase_order_ids.id
        return action
