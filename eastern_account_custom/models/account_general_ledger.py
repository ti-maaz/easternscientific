import json

from odoo import models


class AccountGeneralLedgerReportHandler(models.AbstractModel):
    _inherit = "account.general.ledger.report.handler"

    def _report_custom_engine_general_ledger(
        self,
        expressions,
        options,
        date_scope,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
        warnings=None,
    ):
        result = super()._report_custom_engine_general_ledger(
            expressions,
            options,
            date_scope,
            current_groupby,
            next_groupby,
            offset=offset,
            limit=limit,
            warnings=warnings,
        )

        if current_groupby == "id_with_accumulated_balance":
            line_ids_by_key = {
                key: json.loads(key)[1]
                for key, values in result
                if "balance_line" not in key
            }
            cheque_by_line = {
                line.id: line.cheque_number
                for line in self.env["account.move.line"].browse(
                    line_ids_by_key.values()
                )
            }
            for key, values in result:
                values["cheque_number"] = cheque_by_line.get(
                    line_ids_by_key.get(key)
                ) or ""
        elif current_groupby:
            for _key, values in result:
                values["cheque_number"] = ""
        else:
            result["cheque_number"] = ""

        return result
