from psycopg2 import IntegrityError

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestVendorShipment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create(
            {"name": "Test Vendor", "email": "vendor@example.com"}
        )
        cls.other_vendor = cls.env["res.partner"].create(
            {"name": "Other Vendor", "email": "other@example.com"}
        )
        cls.purchase_order = cls.env["purchase.order"].create(
            {
                "partner_id": cls.vendor.id,
                "partner_ref": "V-100",
                "company_id": cls.env.company.id,
            }
        )

    def test_sequence_and_confirmation_composer(self):
        shipment = self.env["vendor.shipment"].create(
            {
                "vendor_id": self.vendor.id,
                "purchase_order_ids": [(6, 0, self.purchase_order.ids)],
                "shipment_etd": "2026-09-20",
                "shipment_eta": "2026-10-15",
            }
        )
        self.assertTrue(shipment.name.startswith("SHP/"))
        action = shipment.action_send_confirmation()
        self.assertEqual(action["res_model"], "mail.compose.message")
        self.assertEqual(action["context"]["default_partner_ids"], self.vendor.ids)

        template = self.env.ref(
            "vendor_shipment_tracking.mail_template_shipment_confirmation"
        )
        rendered = template._generate_template(
            shipment.ids, {"subject", "body_html"}
        )[shipment.id]
        self.assertIn(shipment.name, rendered["subject"])
        self.assertIn(self.purchase_order.name, rendered["body_html"])

        shipment.with_context(mark_shipment_confirmation_as_sent=True).message_post(
            body="Confirmation request", partner_ids=self.vendor.ids
        )
        self.assertEqual(shipment.confirmation_status, "sent")
        self.assertEqual(shipment.last_confirmation_recipient_ids, self.vendor)

    def test_missing_recipient_email_is_rejected(self):
        vendor = self.env["res.partner"].create({"name": "No Email Vendor"})
        shipment = self.env["vendor.shipment"].create({"vendor_id": vendor.id})
        with self.assertRaises(UserError):
            shipment.action_send_confirmation()

    def test_mismatched_purchase_order_vendor_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.env["vendor.shipment"].create(
                {
                    "vendor_id": self.other_vendor.id,
                    "purchase_order_ids": [(6, 0, self.purchase_order.ids)],
                }
            )

    def test_eta_must_not_precede_etd(self):
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.env["vendor.shipment"].create(
                    {
                        "vendor_id": self.vendor.id,
                        "shipment_etd": "2026-10-15",
                        "shipment_eta": "2026-09-20",
                    }
                )
