from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    tax_invoice_sequence_id = fields.Many2one(
        related="company_id.tax_invoice_sequence_id",
        readonly=False,
        check_company=True,
        domain="[('company_id', '=', company_id)]",
    )
    without_tax_invoice_sequence_id = fields.Many2one(
        related="company_id.without_tax_invoice_sequence_id",
        readonly=False,
        check_company=True,
        domain="[('company_id', '=', company_id)]",
    )
