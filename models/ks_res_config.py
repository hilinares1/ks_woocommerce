from odoo import models


class KsResConfigSettingsInherit(models.TransientModel):
    _inherit = 'res.config.settings'

    def set_values(self):
        """
        Adding security rule for product tag

        :return: None
        """
        super(KsResConfigSettingsInherit, self).set_values()
        rule = self.env.ref('ks_woocommerce.ks_woo_product_tag_security_rule', False)
        if rule:
            rule.write({'active': not bool(self.company_share_product)})
