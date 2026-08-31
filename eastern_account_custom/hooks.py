def post_init_hook(env):
    env["res.company"].search([])._ensure_eastern_invoice_sequences()


def uninstall_hook(env):
    companies = env["res.company"].search([])
    generated_sequences = env["ir.sequence"].search(
        [
            "|",
            ("code", "=like", "eastern.tax.invoice.%"),
            ("code", "=like", "eastern.without.tax.invoice.%"),
        ]
    )
    companies.write(
        {
            "tax_invoice_sequence_id": False,
            "without_tax_invoice_sequence_id": False,
        }
    )
    generated_sequences.unlink()
