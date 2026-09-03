# RAF Traders Website

Odoo 19 website module that serves the captured RAF Traders catalogue on the
public routes while keeping the Odoo backend available at `/web`.

## Odoo.sh

The module is intended for the `testing` branch. Odoo.sh development builds use
**Install only my modules** by default, which installs this module automatically.
If the branch is moved to Staging and uses an existing production database,
install **RAF Traders Website** from Apps once before testing it.

The catalogue content is a static WordPress mirror. Visual pages, navigation,
images, fonts, and client-side effects are included. Inquiry and newsletter
forms are bridged to Odoo CRM leads. WordPress-only commerce endpoints such as
cart, checkout, and customer accounts are not provided by this module.
