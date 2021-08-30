# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from werkzeug import urls
from odoo.exceptions import ValidationError
from odoo.http import request


class KsWooProductVariantImage(models.Model):
    _name = 'ks.woo.product.variant.image'
    _description = 'Woo Product Variant Image'
    _order = 'sequence asc'

    ks_file_name = fields.Char('Image Name', required=True)
    ks_image = fields.Binary('Image', required="True")
    ks_woo_instance_id = fields.Many2one('ks.woocommerce.instances', 'Instance',
                                         related='ks_product_variant_id.ks_woo_instance_id')
    ks_woo_id = fields.Integer('WooCommerce Id', readonly=True, default=0)
    ks_product_variant_id = fields.Many2one('product.product')
    sequence = fields.Integer()

    def ks_variant_woo_image_url(self, template_id, image_id, filename):
        """
        :param template_id: Product Id
        :param image_id: Product Image Id
        :param filename: Product Image File Name
        :return: This will return the public image url
        """
        ext = len(filename.split('.'))
        if not ext > 1:
            filename = filename + '.jpg'
        base_url = '/' if self.env.context.get('relative_url') else \
            self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        public_url = urls.url_join(base_url, "/ks_woo_image/variant/%s/%s/%s/%s/%s" % (request.session.db, self.env.user.id, template_id, image_id, filename))
        return public_url

class KsWooProductVariant(models.Model):
    _inherit = 'product.product'

    ks_variant_weight = fields.Float()
    ks_variant_volume = fields.Float()
    ks_variant_length = fields.Float(help="""ks_variant_length:This stores variant length """)
    ks_variant_width = fields.Float(help="""ks_variant_width:This stores variant width """)
    ks_variant_height = fields.Float(help="""ks_variant_height:This stores variant height """)

    ks_woo_variant_id = fields.Integer('Woo Variant Id', track_visibility='onchange',default=0,
                                       help="""Woo Id: Unique WooCommerce resource id for the product variant on the 
                                       specified WooCommerce Instance""")
    ks_date_variant_created = fields.Datetime('Variant Created On',
                                              readonly=True,
                                              help="Created On: Date on which the WooCommerce Product has been created")
    ks_date_variant_updated = fields.Datetime('Variant Updated On',
                                              readonly=True,
                                              help="Updated On: Date on which the WooCommerce Product has been last "
                                                   "updated")
    ks_woo_variant_description = fields.Text(
                                             help="""Description: An optional description for 
                                                                           this wooCommerce product variant""")
    ks_variant_exported_in_woo = fields.Boolean('Variant Exported in Woo',
                                                store=True,
                                                compute='_ks_compute_export_in_woo',
                                                help="""Exported in Woo: If enabled, the product is synced with the specified 
                                                WooCommerce Instance""")
    ks_woo_variant_reg_price = fields.Float('Woo Regular Price')
    ks_woo_variant_sale_price = fields.Float('Woo Sale price')
    ks_file_type = fields.Char(string='FileType')
    ks_variant_profile_image = fields.Binary()
    ks_product_image_id = fields.Many2one('ks.woo.product.variant.image',
                                          help="""Gallery Images: This includes all the images for the synced product
                                                         including the display image.""")
    ks_woo_regular_pricelist = fields.Many2one('product.pricelist', string="Regular Pricelist", readonly=True,
                                               compute="ks_update_pricelist")
    ks_woo_sale_pricelist = fields.Many2one('product.pricelist', string="Sale Pricelist", readonly=True,
                                            compute="ks_update_pricelist")

    @api.onchange('ks_woo_variant_reg_price', 'ks_woo_variant_sale_price')
    def ks_onchange_variant_price(self):
        """
        Update on the Product Variant Price

        :return: None
        """
        for rec in self:
            if rec.ks_woo_variant_reg_price:
                if rec.ks_woo_variant_reg_price <= rec.ks_woo_variant_sale_price:
                    raise ValidationError(_("Sale price cannot be more than Regular price !"))
            if rec.ks_woo_variant_sale_price:
                if rec.ks_woo_variant_reg_price <= rec.ks_woo_variant_sale_price:
                    raise ValidationError(_("Sale price cannot be more than Regular price !"))

    @api.constrains('ks_woo_variant_reg_price')
    def change_regular_price_in_pricelist(self):
        """
        This function is used to update the regular pricelist when there is any change in the regular price on product variant

        :return: none
        """
        for rec in self:
            ks_pricelist_item_check = rec.ks_woo_instance_id.ks_woo_pricelist.item_ids.search(
                [('pricelist_id', '=', rec.ks_woo_instance_id.ks_woo_pricelist.id),
                 ('applied_on', '=', '0_product_variant'),
                 ('product_id', '=', rec.id),
                 ('compute_price', '=', 'fixed'),
                 ('ks_instance_id', '=', rec.ks_woo_instance_id.id)],
                limit=1)
            if ks_pricelist_item_check:
                if rec.ks_woo_variant_reg_price >= rec.ks_woo_variant_sale_price:
                    if not ks_pricelist_item_check.fixed_price == rec.ks_woo_variant_reg_price:
                        ks_pricelist_item_check.fixed_price = rec.ks_woo_variant_reg_price

    @api.constrains('ks_woo_variant_sale_price')
    def change_sale_price_in_pricelist(self):
        """
        This function is used to update the sale pricelist when there is any change in the sale price on product variant

        :return: none
        """
        for rec in self:
            ks_pricelist_item_check = rec.ks_woo_instance_id.ks_woo_sale_pricelist.item_ids.search(
                [('pricelist_id', '=', rec.ks_woo_instance_id.ks_woo_sale_pricelist.id),
                 ('applied_on', '=', '0_product_variant'),
                 ('product_id', '=', rec.id),
                 ('compute_price', '=', 'fixed'),
                 ('ks_instance_id', '=', rec.ks_woo_instance_id.id)],
                limit=1)
            if ks_pricelist_item_check:
                if rec.ks_woo_variant_sale_price <= rec.ks_woo_variant_reg_price:
                    if not ks_pricelist_item_check.fixed_price == rec.ks_woo_variant_sale_price:
                        ks_pricelist_item_check.fixed_price = rec.ks_woo_variant_sale_price
                else:
                    raise ValidationError("Sale price cannot be more than Regular price !")

    def ks_update_pricelist(self):
        """
        This function is used to set the regular and onsale pricelist on the product variant view

        :return: none
        """
        for rec in self:
            rec.ks_woo_regular_pricelist = rec.ks_woo_instance_id.ks_woo_pricelist.id
            rec.ks_woo_sale_pricelist = rec.ks_woo_instance_id.ks_woo_sale_pricelist.id

    def open_variant_reg_pricelist_rules_data(self):
        """
        This function is used to open the regular pricelist tree view with respective product variant

        :return: Tree View of the pricelist
        """
        self.ensure_one()
        domain = [
            ('product_tmpl_id', '=', self.product_tmpl_id.id),
            ('product_id', '=', self.id),
            ('currency_id', '=', self.ks_woo_instance_id.ks_woo_currency.id),
            ('pricelist_id', '=', self.ks_woo_regular_pricelist.id)
        ]
        return {
            'name': _('Price Rules'),
            'view_mode': 'tree,form',
            'views': [(self.env.ref('ks_woocommerce.product_pricelist_item_tree_view_product').id, 'tree'),
                      (False, 'form')],
            'res_model': 'product.pricelist.item',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': domain,
            'context': {
                'default_product_tmpl_id': self.id,
                'default_applied_on': '1_product',
                'product_without_variants': self.product_variant_count == 1,
            },
        }

    def open_variant_sale_pricelist_rules_data(self):
        """
        This function is used to open the sale pricelist tree view with respective product variant

        :return: Tree view of the pricelist
        """
        self.ensure_one()
        domain = [
            ('product_tmpl_id', '=', self.product_tmpl_id.id),
            ('product_id', '=', self.id),
            ('currency_id', '=', self.ks_woo_instance_id.ks_woo_currency.id),
            ('pricelist_id', '=', self.ks_woo_sale_pricelist.id)
        ]
        return {
            'name': _('Price Rules'),
            'view_mode': 'tree,form',
            'views': [(self.env.ref('ks_woocommerce.product_pricelist_item_tree_view_product').id, 'tree'),
                      (False, 'form')],
            'res_model': 'product.pricelist.item',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': domain,
            'context': {
                'default_product_tmpl_id': self.id,
                'default_applied_on': '1_product',
                'product_without_variants': self.product_variant_count == 1,
            },
        }

    @api.onchange('ks_variant_profile_image')
    def _variant_onchange_image(self):
        """
        This function is used to create record for variant product image update

        :return: none
        """
        for rec in self:
            if not rec.ks_file_type == rec.ks_product_image_id.ks_file_name:
                data = self.env['ks.woo.product.variant.image'].create({
                    'ks_file_name': rec.ks_file_type,
                    'ks_image': rec.ks_variant_profile_image,
                    'ks_product_variant_id': rec.id,
                })
                rec.ks_product_image_id = data.id
            if not rec.ks_variant_profile_image:
                rec.ks_product_image_id = False

    def write(self, vals):
        """
        Updating the Datetime on every change in data

        :param values: Change data
        :return: None
        """
        for rec in self:
            if rec.ks_woo_id:
                rec.product_tmpl_id.ks_sync_date = datetime.datetime.now()
        res = super(KsWooProductVariant, self).write(vals)
        return res

    @api.depends('ks_woo_variant_id')
    def _ks_compute_export_in_woo(self):
        """
        This will make enable the Exported in Woo if record has the WooCommerce Id

        :return: None
        """
        for rec in self:
            rec.ks_variant_exported_in_woo = bool(rec.ks_woo_variant_id)

    @api.onchange('ks_variant_length', 'ks_variant_width', 'ks_variant_height')
    def ks_onchange_l_b_h(self):
        """
        This will calculate the value for Volume with respective of ks_length, ks_width and ks_height

        :return: None
        """
        self.ks_variant_volume = float(self.ks_variant_length if self.ks_variant_length else 0) * float(
            self.ks_variant_width if self.ks_variant_width else 0) * float(
            self.ks_variant_height if self.ks_variant_height else 0)

    def ks_prepare_product_variant_data(self, json_data):
        """
        Prepare Product Variant Data for the odoo

        :param json_data: Woocommerce Data
        :return: Data
        """
        data = {
            "active": True,
            "default_code": json_data.get('sku') or '',
            "ks_variant_weight": json_data.get('weight') or '',
            "ks_variant_length": json_data.get('dimensions').get('length') or '',
            "ks_variant_height": json_data.get('dimensions').get('height') or '',
            "ks_variant_width": json_data.get('dimensions').get('width') or '',
            "ks_variant_volume": float(json_data.get('dimensions').get('length') or 0.0) * float(
                json_data.get('dimensions').get('height') or 0.0) * float(
                json_data.get('dimensions').get('width') or 0.0),
	        "ks_variant_profile_image": self.env['product.template'].ks_image_read_from_url(json_data.get('image')),
            "ks_woo_variant_id": json_data.get('id') or '',
            "ks_date_variant_created": datetime.datetime.strptime((json_data.get('date_created')).replace('T', ' '),
                                                         DEFAULT_SERVER_DATETIME_FORMAT) if json_data.get('date_created') else False,
            "ks_date_variant_updated": datetime.datetime.strptime((json_data.get('date_modified')).replace('T', ' '),
                                                         DEFAULT_SERVER_DATETIME_FORMAT) if json_data.get('date_modified') else False,
            "ks_woo_variant_description": json_data.get('description') or '',

        }
        return data

    def ks_update_price_on_product_variant(self, json_data):
        """
        Update Price on the Product Variant

        :param json_data: Woocommerce Data
        :return: None
        """
        pricelists = self.ks_woo_instance_id.ks_woo_sale_pricelist.search(
            [('ks_instance_id', '=', self.ks_woo_instance_id.id), ('ks_onsale_pricelist', '=', True),
             ('currency_id', '=', self.ks_woo_instance_id.ks_woo_currency.id), ])
        self.ks_woo_variant_reg_price = float(json_data.get('regular_price') or 0.0)
        self.ks_woo_variant_sale_price = float(self.ks_woo_instance_id.ks_woo_sale_pricelist.search(
                [('ks_instance_id', '=', self.ks_woo_instance_id.id),
                 ('currency_id', '=', self.ks_woo_instance_id.ks_woo_currency.id),
                 ('ks_onsale_pricelist', '=', True)]).item_ids.search([('pricelist_id', '=', pricelists.id),
                                                                       ('applied_on', '=', '0_product_variant'),
                                                                       ('product_id', '=', self.id),
                                                                       ('compute_price', '=', 'fixed'),
                                                                       ('ks_instance_id', '=',
                                                                        self.ks_woo_instance_id.id)]).fixed_price or
                                               (json_data.get('sale_price') or 0.0))
        self.list_price = self.ks_woo_sale_price if self.ks_woo_sale_price else self.ks_woo_regular_price
        instance_id = self.ks_woo_instance_id
        ks_pricelists = instance_id.ks_woo_pricelist_ids
        if not ks_pricelists:
            ks_pricelists = []
            ks_pricelists.append(instance_id.ks_woo_pricelist)
            ks_pricelists.append(instance_id.ks_woo_sale_pricelist)
        else:
            ks_pricelists = []
            for data in instance_id.ks_woo_pricelist_ids.search(
                    [('ks_onsale_pricelist', '=', False), ('ks_instance_id', '=', instance_id.id)]):
                ks_pricelists.append(data)
            for data in instance_id.ks_woo_pricelist_ids.search(
                    [('ks_onsale_pricelist', '=', True), ('ks_instance_id', '=', instance_id.id)]):
                ks_pricelists.append(data)
        for ks_pricelist in ks_pricelists:
            self.env['product.template'].ks_update_price_on_price_list(json_data, ks_pricelist, self, instance_id)
