from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    discount_type = fields.Selection(
        [
            ("percentage", "Percentage"),
            ("fixed", "Fixed Amount"),
        ],
        string="Discount Type",
        default="percentage",
        required=True,
    )
    discount_fixed = fields.Monetary(
        string="Fixed Discount",
        currency_field="currency_id",
        default=0.0,
        help="Total fixed discount for this line, not an amount per unit.",
    )
    cheque_number = fields.Char(
        related="move_id.cheque_number",
        string="Cheque No.",
        store=True,
        index=True,
    )

    @api.onchange("discount_type", "discount_fixed", "quantity", "price_unit")
    def _onchange_eastern_fixed_discount(self):
        for line in self:
            if line.discount_type == "fixed":
                line.discount = line._eastern_fixed_discount_percentage()
            elif line.discount_fixed:
                line.discount_fixed = 0.0

    def _eastern_fixed_discount_percentage(self):
        self.ensure_one()
        gross = abs(self.quantity * self.price_unit)
        return (self.discount_fixed / gross * 100.0) if gross else 0.0

    def _normalize_eastern_discount(self):
        percentage_lines = self.filtered(
            lambda item: item.discount_type == "percentage" and item.discount_fixed
        )
        if percentage_lines:
            super(
                AccountMoveLine,
                percentage_lines.with_context(skip_eastern_discount_sync=True),
            ).write({"discount_fixed": 0.0})

        for line in self.filtered(lambda item: item.discount_type == "fixed"):
            percentage = line._eastern_fixed_discount_percentage()
            if float_compare(line.discount, percentage, precision_digits=8):
                super(
                    AccountMoveLine,
                    line.with_context(skip_eastern_discount_sync=True),
                ).write({"discount": percentage})

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._normalize_eastern_discount()
        return lines

    def write(self, vals):
        if self.env.context.get("skip_eastern_discount_sync"):
            return super().write(vals)

        result = super().write(vals)
        if {
            "discount_type",
            "discount_fixed",
            "discount",
            "quantity",
            "price_unit",
        } & vals.keys():
            self._normalize_eastern_discount()
        return result

    @api.constrains("discount_type", "discount_fixed", "quantity", "price_unit")
    def _check_eastern_fixed_discount(self):
        for line in self.filtered(lambda item: item.discount_type == "fixed"):
            gross = abs(line.quantity * line.price_unit)
            if line.discount_fixed < 0:
                raise ValidationError(_("A fixed discount cannot be negative."))
            if float_compare(line.discount_fixed, gross, precision_rounding=line.currency_id.rounding) > 0:
                raise ValidationError(
                    _("The fixed discount cannot exceed the line's gross amount.")
                )
