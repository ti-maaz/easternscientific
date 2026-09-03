from urllib.parse import urlsplit

from markupsafe import escape
from werkzeug.exceptions import Forbidden, NotFound

from odoo import http
from odoo.addons.website.controllers.main import Website
from odoo.http import request
from odoo.tools import email_normalize


_PAGE_PATHS = (
    "about",
    "blog",
    "contact-us",
    "gallery",
    "product-category/heidelberg-offset-four-color-printing-machine",
    "product-category/heidelberg-offset-one-color-printing-machine",
    "product-category/heidelberg-offset-six-color-printing-machine",
    "product-category/heidelberg-offset-two-color-printing-machine",
    "product/2010-gallus-label-printing-2010-used-machine-for-sale",
    "product/gw-d-150-twin-knife-sheeter",
    "product/heidelberg-offset-two-color-printing-machine",
    "product/spare-parts-muller-martini-progress",
)

_PAGE_ROUTES = [f"/{path}/" for path in _PAGE_PATHS]
_LEGACY_PAGE_ROUTES = ["/index.html", *[f"/{path}/index.html" for path in _PAGE_PATHS]]

# The mirrored Elementor pages use inline CSS/JavaScript and a small number of
# live third-party embeds. Keep the policy explicit while allowing those pages
# to run exactly as captured.
_CONTENT_SECURITY_POLICY = (
    "default-src 'self' https: data: blob:; "
    "script-src 'self' https: 'unsafe-inline' 'unsafe-eval' blob:; "
    "style-src 'self' https: 'unsafe-inline'; "
    "img-src 'self' https: data: blob:; "
    "font-src 'self' https: data:; "
    "frame-src https:; "
    "connect-src 'self' https:; "
    "object-src 'none'; "
    "base-uri 'self';"
)


class RafTraderWebsite(Website):
    """Serve the captured RAF Traders website without hiding Odoo's /web UI."""

    @staticmethod
    def _serve_page(relative_path):
        try:
            stream = http.Stream.from_path(
                f"raf_trader_website/site/{relative_path}",
                filter_ext=(".html",),
                public=True,
            )
        except (FileNotFoundError, ValueError):
            raise NotFound() from None

        response = stream.get_response(
            max_age=300,
            content_security_policy=_CONTENT_SECURITY_POLICY,
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @http.route()
    def index(self, **kwargs):
        return self._serve_page("index.html")

    @http.route(
        _PAGE_ROUTES,
        type="http",
        auth="public",
        website=True,
        sitemap=True,
        methods=["GET"],
        readonly=True,
    )
    def raf_page(self, **kwargs):
        page_path = request.httprequest.path.strip("/")
        if page_path not in _PAGE_PATHS:
            raise NotFound()
        return self._serve_page(f"{page_path}/index.html")

    @http.route(
        _LEGACY_PAGE_ROUTES,
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        methods=["GET"],
        readonly=True,
    )
    def raf_legacy_page(self, **kwargs):
        path = request.httprequest.path
        canonical_path = path.removesuffix("index.html") or "/"
        return request.redirect(canonical_path, code=301)

    @http.route(
        [
            "/wp-content/<path:asset_path>",
            "/wp-includes/<path:asset_path>",
            "/_external/<path:asset_path>",
        ],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        methods=["GET"],
        readonly=True,
    )
    def raf_asset(self, asset_path, **kwargs):
        asset_root = request.httprequest.path.split("/", 2)[1]
        if asset_root not in {"wp-content", "wp-includes", "_external"}:
            raise NotFound()

        try:
            stream = http.Stream.from_path(
                f"raf_trader_website/site/{asset_root}/{asset_path}",
                public=True,
            )
        except (FileNotFoundError, OSError, ValueError):
            raise NotFound() from None

        # Google Fonts exposes its stylesheet at an extensionless `/css` URL.
        # Python's mimetype detector cannot infer that type from the filename.
        if asset_root == "_external" and asset_path == "fonts.googleapis.com/css":
            stream.mimetype = "text/css"

        return stream.get_response(immutable=True, content_security_policy=None)

    @http.route(
        "/raf-trader/inquiry",
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        methods=["POST"],
        csrf=False,
    )
    def raf_inquiry(self, **post):
        origin = request.httprequest.headers.get("Origin")
        if origin and urlsplit(origin).netloc != request.httprequest.host:
            raise Forbidden()

        email = (post.get("form_fields[email]") or "").strip()[:254]
        normalized_email = email_normalize(email)
        if not normalized_email:
            return request.make_json_response(
                {"ok": False, "message": "Please enter a valid email address."},
                status=400,
            )

        contact_name = (post.get("form_fields[name]") or "").strip()[:255]
        company_name = (post.get("form_fields[field_7af8114]") or "").strip()[:255]
        phone = (post.get("form_fields[field_cd57e72]") or "").strip()[:64]
        message = (post.get("form_fields[message]") or "").strip()[:5000]
        source_url = (post.get("source_url") or "").strip()[:1000]
        is_newsletter = post.get("form_id") == "61a7efa"

        lead_values = {
            "name": (
                f"Newsletter subscription: {normalized_email}"
                if is_newsletter
                else f"Website inquiry: {contact_name or normalized_email}"
            ),
            "type": "lead",
            "contact_name": contact_name or False,
            "partner_name": company_name or False,
            "email_from": normalized_email,
            "phone": phone or False,
            "company_id": request.website.company_id.id,
            "description": (
                f"<p>{escape(message)}</p>" if message else ""
            )
            + (f"<p><strong>Source:</strong> {escape(source_url)}</p>" if source_url else ""),
        }

        lead_model = request.env["crm.lead"].sudo()
        if is_newsletter:
            existing_lead = lead_model.search(
                [
                    ("email_normalized", "=", normalized_email),
                    ("name", "ilike", "Newsletter subscription:%"),
                ],
                limit=1,
            )
            if not existing_lead:
                lead_model.create(lead_values)
        else:
            lead_model.create(lead_values)

        return request.make_json_response(
            {
                "ok": True,
                "message": (
                    "Thank you. Your email has been added."
                    if is_newsletter
                    else "Thank you. Your inquiry has been received."
                ),
            }
        )
