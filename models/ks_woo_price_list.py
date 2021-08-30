# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class KsProductPricelistInherit(models.Model):
    _inherit = 'product.pricelist'

    ks_instance_id = fields.Many2one('ks.woocommerce.instances', string='WooCommerce Instance ID',
                                     help="""WooCommerce Instance: The Instance which will used this price list to update the price""")
    ks_onsale_pricelist = fields.Boolean('OnSale Pricelist', default=False)


class KsProductPricelistItemInherit(models.Model):
    _inherit = 'product.pricelist.item'

    ks_on_sale_price = fields.Boolean('WooCommerce OnSale Price',
                                      help="""OnSale Price: Enable if you want to update Sale Price of WooCommerce Product \n
                                                            Disable if you want to update Regular Price of WooCommerce Product""", compute='ks_is_on_sale_pricelist')
    ks_instance_id = fields.Many2one('ks.woocommerce.instances', related='pricelist_id.ks_instance_id',
                                     string='WooCommerce Instance',
                                     help="""WooCommerce Instance: The Instance which will used this price list to update the price""",
                                     readonly=1)

    def ks_is_on_sale_pricelist(self):
        """
        This function is used to differentiate between onsale and regular pricelist

        :return: none
        """
        for rec in self:
            if rec.pricelist_id.ks_onsale_pricelist:
                rec.ks_on_sale_price = True
            else:
                rec.ks_on_sale_price = False

    @api.constrains('fixed_price')
    def onchange_fixed_price(self):
        """
        This function is used to change the price on the product whenever there is change on the price in the pricelist

        :return: none
        """
        if self.pricelist_id.id == self.ks_instance_id.ks_woo_pricelist.id or self.pricelist_id.id == self.ks_instance_id.ks_woo_sale_pricelist.id:
            if self.product_tmpl_id.ks_woo_product_type == 'variable':
                ks_woo_regular_price = self.product_id.ks_woo_variant_reg_price
                ks_woo_sale_price = self.product_id.ks_woo_variant_sale_price
            else:
                ks_woo_regular_price = self.product_tmpl_id.ks_woo_regular_price
                ks_woo_sale_price = self.product_tmpl_id.ks_woo_sale_price
            if self.ks_on_sale_price:
                if ks_woo_regular_price >= self.fixed_price and (self.product_id or self.product_tmpl_id):
                    if self.product_tmpl_id.ks_woo_product_type == 'variable' and not self.product_id.ks_woo_variant_sale_price == self.fixed_price:
                        self.product_id.ks_woo_variant_sale_price = self.fixed_price
                    elif self.product_tmpl_id.ks_woo_product_type != 'variable' and not self.product_tmpl_id.ks_woo_sale_price == self.fixed_price:
                        self.product_tmpl_id.ks_woo_sale_price = self.fixed_price
                elif self.product_id or self.product_tmpl_id:
                    raise ValidationError("Sale price cannot be greater than Regular Price !")
                if self.fixed_price != 0 and not self.product_id.ks_woo_product_type == 'variable':
                    self.product_tmpl_id.list_price = self.fixed_price
            elif not self.ks_on_sale_price:
                if ks_woo_sale_price <= self.fixed_price or self.fixed_price <= ks_woo_regular_price and (self.product_id or self.product_tmpl_id):
                    if self.product_id.ks_woo_product_type == 'variable':
                        self.product_id.ks_woo_variant_reg_price = self.fixed_price
                    else:
                        self.product_tmpl_id.ks_woo_regular_price = self.fixed_price
                elif self.product_id or self.product_tmpl_id:
                    raise ValidationError("Regular price cannot be less than Sale Price !")
                if self.product_tmpl_id.ks_woo_sale_price == 0 and not self.product_tmpl_id.ks_woo_product_type == 'variable':
                    self.product_tmpl_id.list_price = self.fixed_price