from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestRafTraderWebsiteRoutes(HttpCase):
    def test_public_pages_and_assets(self):
        homepage = self.url_open("/")
        self.assertEqual(homepage.status_code, 200)
        self.assertIn(b"RAF TRADERS", homepage.content.upper())

        footer_links = (
            b'href="/about/"',
            b'href="/blog/"',
            b'href="/contact-us/"',
            b'href="/delivery-information/"',
            b'href="/gallery/"',
            b'href="/privacy-policy/"',
            b'href="/site-map/"',
            b'href="/terms-and-conditions/"',
        )
        for footer_link in footer_links:
            self.assertIn(footer_link, homepage.content)

        about_page = self.url_open("/about/")
        self.assertEqual(about_page.status_code, 200)

        logo = self.url_open(
            "/wp-content/uploads/2026/07/Raftraders-logo-400x117.webp"
        )
        self.assertEqual(logo.status_code, 200)
        self.assertEqual(logo.headers["Content-Type"], "image/webp")

    def test_under_construction_pages(self):
        pages = (
            "/delivery-information/",
            "/privacy-policy/",
            "/site-map/",
            "/terms-and-conditions/",
        )
        for page in pages:
            response = self.url_open(page)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"under construction", response.content.lower())

    def test_odoo_backend_remains_available(self):
        response = self.url_open("/web/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Odoo", response.content)

    def test_inquiry_creates_crm_lead(self):
        response = self.url_open(
            "/raf-trader/inquiry",
            data={
                "form_id": "8a14fea",
                "form_fields[name]": "Test Buyer",
                "form_fields[field_7af8114]": "Test Press Ltd",
                "form_fields[email]": "buyer@example.com",
                "form_fields[field_cd57e72]": "+92 300 1234567",
                "form_fields[message]": "Looking for a four-color press.",
                "source_url": "/",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

        lead = self.env["crm.lead"].search(
            [("email_normalized", "=", "buyer@example.com")],
            limit=1,
        )
        self.assertTrue(lead)
        self.assertEqual(lead.contact_name, "Test Buyer")
        self.assertEqual(lead.partner_name, "Test Press Ltd")

    def test_inquiry_rejects_invalid_email(self):
        response = self.url_open(
            "/raf-trader/inquiry",
            data={
                "form_id": "8a14fea",
                "form_fields[email]": "not-an-email",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])
