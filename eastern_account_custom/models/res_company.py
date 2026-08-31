from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

    tax_invoice_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Tax Invoice Sequence",
        check_company=True,
        domain="[('company_id', '=', id)]",
        ondelete="restrict",
    )
    without_tax_invoice_sequence_id = fields.Many2one(
        "ir.sequence",
        string="Without-Tax Invoice Sequence",
        check_company=True,
        domain="[('company_id', '=', id)]",
        ondelete="restrict",
    )

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._ensure_eastern_invoice_sequences()
        return companies

    def _ensure_eastern_invoice_sequences(self):
        sequence_model = self.env["ir.sequence"].sudo()
        for company in self:
            values = {}
            if not company.tax_invoice_sequence_id:
                values["tax_invoice_sequence_id"] = sequence_model.create(
                    {
                        "name": f"{company.name}: Tax Invoices",
                        "code": f"eastern.tax.invoice.{company.id}",
                        "prefix": "TAX/%(year)s/",
                        "padding": 5,
                        "implementation": "no_gap",
                        "use_date_range": True,
                        "company_id": company.id,
                    }
                ).id
            if not company.without_tax_invoice_sequence_id:
                values["without_tax_invoice_sequence_id"] = sequence_model.create(
                    {
                        "name": f"{company.name}: Without-Tax Invoices",
                        "code": f"eastern.without.tax.invoice.{company.id}",
                        "prefix": "NTX/%(year)s/",
                        "padding": 5,
                        "implementation": "no_gap",
                        "use_date_range": True,
                        "company_id": company.id,
                    }
                ).id
            if values:
                company.sudo().write(values)

    @api.constrains("tax_invoice_sequence_id", "without_tax_invoice_sequence_id")
    def _check_eastern_invoice_sequences(self):
        for company in self:
            sequences = (
                company.tax_invoice_sequence_id
                | company.without_tax_invoice_sequence_id
            )
            if (
                company.tax_invoice_sequence_id
                and company.tax_invoice_sequence_id
                == company.without_tax_invoice_sequence_id
            ):
                raise ValidationError(
                    _("Tax and Without-Tax invoices must use different sequences.")
                )
            if sequences.filtered(lambda sequence: sequence.company_id != company):
                raise ValidationError(
                    _("Invoice sequences must belong to the company they configure.")
                )
