from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestEasternAccount(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.company._ensure_eastern_invoice_sequences()

    def _create_invoice(self, invoice_type="without_tax", lines=None):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "eastern_invoice_type": invoice_type,
                "invoice_line_ids": lines
                or [
                    (
                        0,
                        0,
                        {
                            "name": "Test line",
                            "quantity": 1.0,
                            "price_unit": 100.0,
                            "account_id": self.company_data["default_account_revenue"].id,
                        },
                    )
                ],
            }
        )

    def test_percentage_discount(self):
        invoice = self._create_invoice(
            lines=[
                (
                    0,
                    0,
                    {
                        "name": "Percentage discount",
                        "quantity": 2.0,
                        "price_unit": 100.0,
                        "discount_type": "percentage",
                        "discount": 10.0,
                        "account_id": self.company_data["default_account_revenue"].id,
                    },
                )
            ]
        )
        self.assertRecordValues(invoice.invoice_line_ids, [{"price_subtotal": 180.0}])

    def test_fixed_discount(self):
        invoice = self._create_invoice(
            lines=[
                (
                    0,
                    0,
                    {
                        "name": "Fixed discount",
                        "quantity": 2.0,
                        "price_unit": 100.0,
                        "discount_type": "fixed",
                        "discount_fixed": 50.0,
                        "account_id": self.company_data["default_account_revenue"].id,
                    },
                )
            ]
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [{"discount": 25.0, "price_subtotal": 150.0}],
        )
        invoice.invoice_line_ids.discount = 5.0
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [{"discount": 25.0, "discount_fixed": 50.0, "price_subtotal": 150.0}],
        )

    def test_zero_discount_and_multiple_lines(self):
        invoice = self._create_invoice(
            lines=[
                (
                    0,
                    0,
                    {
                        "name": "No discount",
                        "quantity": 1.0,
                        "price_unit": 100.0,
                        "account_id": self.company_data["default_account_revenue"].id,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "name": "Fixed discount",
                        "quantity": 1.0,
                        "price_unit": 100.0,
                        "discount_type": "fixed",
                        "discount_fixed": 20.0,
                        "account_id": self.company_data["default_account_revenue"].id,
                    },
                ),
            ]
        )
        self.assertEqual(invoice.amount_untaxed, 180.0)

    def test_tax_with_fixed_discount(self):
        invoice = self._create_invoice(
            invoice_type="tax",
            lines=[
                (
                    0,
                    0,
                    {
                        "name": "Taxed fixed discount",
                        "quantity": 1.0,
                        "price_unit": 100.0,
                        "discount_type": "fixed",
                        "discount_fixed": 20.0,
                        "tax_ids": [(6, 0, self.tax_sale_a.ids)],
                        "account_id": self.company_data["default_account_revenue"].id,
                    },
                )
            ],
        )
        self.assertEqual(invoice.amount_untaxed, 80.0)
        self.assertGreater(invoice.amount_tax, 0.0)

    def test_invoice_sequences_and_tax_validation(self):
        without_tax = self._create_invoice()
        without_tax.action_post()
        self.assertTrue(without_tax.name.startswith("NTX/"))

        tax_invoice = self._create_invoice(
            invoice_type="tax",
            lines=[
                (
                    0,
                    0,
                    {
                        "name": "Taxed line",
                        "quantity": 1.0,
                        "price_unit": 100.0,
                        "tax_ids": [(6, 0, self.tax_sale_a.ids)],
                        "account_id": self.company_data["default_account_revenue"].id,
                    },
                )
            ],
        )
        tax_invoice.action_post()
        self.assertTrue(tax_invoice.name.startswith("TAX/"))
        self.assertNotEqual(without_tax.name, tax_invoice.name)

        invalid = self._create_invoice(invoice_type="tax")
        with self.assertRaises(ValidationError):
            invalid.action_post()

        posted_type = without_tax.eastern_invoice_type
        without_tax.button_draft()
        with self.assertRaises(ValidationError):
            without_tax.eastern_invoice_type = "tax"
        self.assertEqual(without_tax.eastern_invoice_type, posted_type)

    def test_failed_and_future_invoices_are_not_numbered(self):
        invalid = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "eastern_invoice_type": "without_tax",
            }
        )
        with self.assertRaises(UserError):
            invalid.action_post()
        self.assertIn(invalid.name, (False, "/"))

        future = self._create_invoice()
        future_date = fields.Date.today() + timedelta(days=1)
        future.write({"invoice_date": future_date, "date": future_date})
        future._post(soft=True)
        self.assertEqual(future.state, "draft")
        self.assertEqual(future.auto_post, "at_date")
        self.assertIn(future.name, (False, "/"))

    def test_cheque_number_is_available_on_journal_items(self):
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": self.company_data["default_journal_misc"].id,
                "cheque_number": "CHQ-001",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Debit",
                            "account_id": self.company_data["default_account_expense"].id,
                            "debit": 100.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Credit",
                            "account_id": self.company_data["default_account_revenue"].id,
                            "credit": 100.0,
                        },
                    ),
                ],
            }
        )
        self.assertEqual(set(move.line_ids.mapped("cheque_number")), {"CHQ-001"})
        move.action_post()

        report = self.env.ref("account_reports.general_ledger_report")
        options = report.get_options({})
        options["unfold_all"] = True
        lines = report._get_lines(options)
        cheque_column_index = next(
            index
            for index, column in enumerate(options["columns"])
            if column["expression_label"] == "cheque_number"
        )
        cheque_values = {
            line["columns"][cheque_column_index].get("no_format")
            or line["columns"][cheque_column_index].get("name")
            for line in lines
            if len(line.get("columns", [])) > cheque_column_index
        }
        self.assertIn("CHQ-001", cheque_values)

        bank_journal = self.company_data["default_journal_bank"]
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "amount": 100.0,
                "journal_id": bank_journal.id,
                "payment_method_line_id": bank_journal.inbound_payment_method_line_ids[0].id,
                "cheque_number": "PAY-CHQ-001",
            }
        )
        payment.action_post()
        self.assertEqual(payment.move_id.cheque_number, "PAY-CHQ-001")
        self.assertEqual(
            set(payment.move_id.line_ids.mapped("cheque_number")),
            {"PAY-CHQ-001"},
        )

    def test_invoice_report_visibility_options(self):
        invoice = self._create_invoice(
            invoice_type="tax",
            lines=[
                (
                    0,
                    0,
                    {
                        "name": "Visible tax and discount",
                        "quantity": 1.0,
                        "price_unit": 100.0,
                        "discount_type": "fixed",
                        "discount_fixed": 20.0,
                        "tax_ids": [(6, 0, self.tax_sale_a.ids)],
                        "account_id": self.company_data["default_account_revenue"].id,
                    },
                )
            ],
        )
        report_action = self.env.ref("account.account_invoices")
        visible_html = report_action._render_qweb_html(
            report_action.report_name, invoice.ids
        )[0]
        self.assertIn(b'name="th_discount"', visible_html)
        self.assertIn(b'name="th_taxes"', visible_html)

        invoice.write(
            {
                "show_tax_details": False,
                "show_invoice_discount_details": False,
            }
        )
        hidden_html = report_action._render_qweb_html(
            report_action.report_name, invoice.ids
        )[0]
        self.assertNotIn(b'name="th_discount"', hidden_html)
        self.assertNotIn(b'name="th_taxes"', hidden_html)
        self.assertIn(b"Amount Total", hidden_html)
