from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    cheque_number = fields.Char(
        string="Cheque No.",
        copy=False,
        index=True,
        tracking=True,
    )

    def _generate_move_vals(self, write_off_line_vals=None, force_balance=None, line_ids=None):
        values = super()._generate_move_vals(
            write_off_line_vals=write_off_line_vals,
            force_balance=force_balance,
            line_ids=line_ids,
        )
        values["cheque_number"] = self.cheque_number
        return values

    def write(self, vals):
        result = super().write(vals)
        if "cheque_number" in vals and not self.env.context.get("skip_cheque_sync"):
            self.move_id.with_context(skip_cheque_sync=True).write(
                {"cheque_number": vals["cheque_number"]}
            )
        return result
