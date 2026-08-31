from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    eastern_invoice_type = fields.Selection(
        [
            ("tax", "Tax Invoice"),
            ("without_tax", "Without Tax"),
        ],
        string="Invoice Type",
        copy=True,
        tracking=True,
    )
    cheque_number = fields.Char(
        string="Cheque No.",
        copy=False,
        index=True,
        tracking=True,
    )
    show_tax_details = fields.Boolean(
        string="Show Tax Details",
        default=True,
        copy=True,
        help="Show tax columns and the tax breakdown on the customer invoice.",
    )
    show_invoice_discount_details = fields.Boolean(
        string="Show Discounts on Invoice",
        default=True,
        copy=True,
        help="Show discount columns on the customer invoice.",
    )

    def _validate_eastern_invoice_type(self):
        for move in self.filtered(lambda item: item.move_type == "out_invoice"):
            if not move.eastern_invoice_type:
                raise ValidationError(_("Select an Invoice Type before posting the invoice."))

            product_lines = move.invoice_line_ids.filtered(
                lambda line: line.display_type == "product"
            )
            taxed_lines = product_lines.filtered("tax_ids")
            if move.eastern_invoice_type == "tax" and not taxed_lines:
                raise ValidationError(_("A Tax Invoice must contain at least one taxed line."))
            if move.eastern_invoice_type == "without_tax" and taxed_lines:
                raise ValidationError(_("A Without-Tax Invoice cannot contain taxed lines."))

    def _set_next_sequence(self):
        self.ensure_one()
        if self.move_type != "out_invoice":
            return super()._set_next_sequence()

        company = self.company_id
        company._ensure_eastern_invoice_sequences()
        sequence = (
            company.tax_invoice_sequence_id
            if self.eastern_invoice_type == "tax"
            else company.without_tax_invoice_sequence_id
        )
        if not sequence:
            invoice_type = dict(
                self._fields["eastern_invoice_type"]._description_selection(self.env)
            )[self.eastern_invoice_type]
            raise UserError(
                _("Configure the %(type)s sequence for %(company)s before posting.",
                  type=invoice_type, company=company.display_name)
            )
        number = sequence.with_context(ir_sequence_date=self.date).next_by_id()
        if not number:
            raise UserError(_("The configured invoice sequence did not generate a number."))
        self.name = number
        self._compute_split_sequence()

    def write(self, vals):
        if "eastern_invoice_type" in vals:
            changed_posted_moves = self.filtered(
                lambda move: move.posted_before
                and move.eastern_invoice_type != vals["eastern_invoice_type"]
            )
            if changed_posted_moves:
                raise ValidationError(
                    _("The Invoice Type cannot be changed after an invoice has been posted.")
                )
        result = super().write(vals)
        if "cheque_number" in vals and not self.env.context.get("skip_cheque_sync"):
            self.origin_payment_id.with_context(skip_cheque_sync=True).write(
                {"cheque_number": vals["cheque_number"]}
            )
        return result

    def _post(self, soft=True):
        customer_invoices = self.filtered(lambda move: move.move_type == "out_invoice")
        customer_invoices._validate_eastern_invoice_type()
        pre_numbered = customer_invoices.filtered(
            lambda move: not move.posted_before and move.name not in (False, "/")
        )
        if pre_numbered:
            raise ValidationError(
                _("Customer invoice numbers are assigned automatically when posting.")
            )
        return super()._post(soft=soft)
