# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import fields, models, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError
from requests.exceptions import ConnectionError
from woocommerce import API as WCAPI
from odoo.http import request


# from wordpress import API as WPAPI


class KsWooCommerceInstance(models.Model):
    _name = 'ks.woocommerce.instances'
    _description = 'WooCommerce Instances Details'
    _rec_name = 'ks_name'
    ks_auth = fields.Boolean('Authorization')
    ks_name = fields.Char('Woo Instance Name', required=True)
    ks_woo_store_url = fields.Char('WooCommerce Store URL', required=True)
    ks_customer_key = fields.Char('Customer Key', required=True)
    ks_customer_secret = fields.Char('Customer Secret', required=True)
    ks_verify_ssl = fields.Boolean('Verify SSL')
    ks_wc_version = fields.Selection([('wc/v3', '3.5.x or later'), ('wc/v2', '3.0.x or later'),
                                      ('wc/v1', '2.6.x or later')],
                                     string='WooCommerce Version', default='wc/v3', readonly=True,
                                     required=True)
    color = fields.Integer(default=10)
    ks_stock_field_type = fields.Many2one('ir.model.fields', 'Stock Field Type',
                                          domain="[('model_id', '=', 'product.product'),"
                                                 "('name', 'in', ['qty_available','virtual_available'])]")
    ks_instance_state = fields.Selection([('draft', 'Draft'), ('connected', 'Connected'), ('active', 'Active'),
                                          ('deactivate', 'Deactivate')], string="Woo Instance State", default="draft")
    ks_instance_connected = fields.Boolean(default=False)
    ks_company = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id, readonly=1)
    ks_warehouse = fields.Many2one('stock.warehouse', 'Warehouse', domain="[('company_id', '=', ks_company)]")
    ks_woo_currency = fields.Many2one('res.currency', 'Currency')
    ks_multi_currency_option = fields.Boolean(string='Multi-Currency Option', default=False)
    ks_woo_multi_currency = fields.Many2many(comodel_name='res.currency', string='Multi-Currency')
    ks_import_order_state_config = fields.One2many('ks.woocommerce.status', 'ks_instance_id')
    ks_sales_team = fields.Many2one('crm.team', string="Sales Team")
    ks_sales_person = fields.Many2one('res.users', string="Sales Person")
    ks_journal_id = fields.Many2one('account.journal', string='Payment Method',
                                    domain=[('type', 'in', ('bank', 'cash'))])
    ks_woo_count_orders = fields.Integer('Order Count', compute='_compute_count_of_woo_records')
    ks_woo_count_products = fields.Integer('Product Count', compute='_compute_count_of_woo_records')
    ks_woo_count_coupons = fields.Integer('Coupon Count', compute='_compute_count_of_woo_records')
    ks_woo_count_customers = fields.Integer('Customer Count', compute='_compute_count_of_woo_records')
    ks_woo_fees = fields.Many2one('product.product', 'Woo Fees')
    ks_woo_shipping = fields.Many2one('product.product', 'Woo Shipping')
    ks_auto_update_stock = fields.Boolean('Auto Update Product Stock?')
    ks_aus_cron_id = fields.Many2one('ir.cron', readonly=1)
    ks_aus_cron_last_updated = fields.Datetime('Last Updated [Product Stock]', readonly=True)
    ks_aus_cron_next_update = fields.Datetime('Next Update [Product Stock]', related='ks_aus_cron_id.nextcall',
                                              readonly=True)
    ks_aus_update_permission = fields.Boolean(string="Update Product Stock", default=False)
    ks_aus_cron_active_permission = fields.Boolean(default=False, string="Active/Inactive Product Stock Cron")
    ks_auto_update_order_status = fields.Boolean('Auto Update Order Status?')
    ks_auos_cron_id = fields.Many2one('ir.cron', readonly=1)
    ks_auos_cron_last_updated = fields.Datetime('Last Updated [Order Status]', readonly=True)
    ks_auos_cron_next_update = fields.Datetime('Next Update [Order Status]', related='ks_auos_cron_id.nextcall',
                                               readonly=True)
    ks_auos_update_permission = fields.Boolean(string="Update Order Status Cron", default=False)
    ks_auos_cron_active_permission = fields.Boolean(default=False, string="Active/Inactive Order Status Cron")
    ks_auto_import_order = fields.Boolean('Auto Import Order?')
    ks_aio_cron_id = fields.Many2one('ir.cron', readonly=1)
    ks_aio_cron_last_updated = fields.Datetime('Last Updated [Sale Order]', readonly=True)
    ks_aio_cron_next_update = fields.Datetime('Next Update [Sale Order]', related='ks_aio_cron_id.nextcall',
                                              readonly=True)
    ks_aio_update_permission = fields.Boolean(string="Update Order Cron", default=False)
    ks_aio_cron_active_permission = fields.Boolean(default=False, string="Active/Inactive Order Update Cron")
    ks_auto_import_product = fields.Boolean('Auto Import Product?')
    ks_aip_cron_id = fields.Many2one('ir.cron', readonly=1)
    ks_aip_cron_last_updated = fields.Datetime('Last Updated [Product]', readonly=True)
    ks_aip_cron_next_update = fields.Datetime('Next Update [Product]', related='ks_aip_cron_id.nextcall',
                                              readonly=True)
    ks_aip_update_permission = fields.Boolean(string="Update Product Cron", default=False)
    ks_aip_cron_active_permission = fields.Boolean(default=False, string="Active/Inactive Product Update Cron")
    ks_woo_customer = fields.Many2one('res.partner', 'Woo Customer')
    ks_base_url = fields.Char(default=lambda self: self.env['ir.config_parameter'].sudo().get_param('web.base.url'))
    ks_order_prefix = fields.Char(string="Order Prefix")
    ks_payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    ks_woo_pricelist = fields.Many2one('product.pricelist', string='Regular Main Pricelist', store=True,
                                       compute='_ks_pricelist_on_currency_change')
    ks_woo_sale_pricelist = fields.Many2one('product.pricelist', string='OnSale Main Pricelist', store=True,
                                            compute='_ks_pricelist_on_currency_change')
    ks_global_discount_enable = fields.Boolean(string='Enable/Disable Global Discount', default=False)
    ks_global_discount = fields.Float(string='Global Discount (%)', default=0.0)
    ks_woo_pricelist_ids = fields.Many2many('product.pricelist', string='Multi-Pricelist', store=True,
                                            compute='_ks_multi_pricelist_on_multi_currency_change')
    ks_id = fields.Char(string="Instance Unique No.", required=True, copy=False, index=True, readonly=True,
                        default='New')
    # Todo these fields are used for cron testing
    # order import cron fields on instance
    ks_cron_aio_schedule_user = fields.Many2one('res.users',
                                                default=lambda self: self.env.user)
    ks_cron_aio_interval_number = fields.Integer(default=1)
    ks_cron_aio_nextcall = fields.Datetime()
    ks_cron_aio_interval_type = fields.Selection([('minutes', 'Minutes'),
                                                  ('hours', 'Hours'),
                                                  ('days', 'Days'),
                                                  ('weeks', 'Weeks'),
                                                  ('months', 'Months')], default='months')
    # product import cron on instance
    ks_cron_ip_schedule_user = fields.Many2one('res.users', default=lambda self: self.env.user)
    ks_cron_ip_interval_number = fields.Integer(default=1)
    ks_cron_ip_nextcall = fields.Datetime()
    ks_cron_ip_interval_type = fields.Selection([('minutes', 'Minutes'),
                                                 ('hours', 'Hours'),
                                                 ('days', 'Days'),
                                                 ('weeks', 'Weeks'),
                                                 ('months', 'Months')], default='months')

    # auto order status update cron from instance
    ks_cron_auos_schedule_user = fields.Many2one('res.users',
                                                 default=lambda self: self.env.user)
    ks_cron_auos_interval_number = fields.Integer(default=1)
    ks_cron_auos_nextcall = fields.Datetime()
    ks_cron_auos_interval_type = fields.Selection([('minutes', 'Minutes'),
                                                   ('hours', 'Hours'),
                                                   ('days', 'Days'),
                                                   ('weeks', 'Weeks'),
                                                   ('months', 'Months')], default='months')

    # auto update stock using cron from instance
    ks_cron_aus_schedule_user = fields.Many2one('res.users',
                                                default=lambda self: self.env.user)
    ks_cron_aus_interval_number = fields.Integer(default=1)
    ks_cron_aus_nextcall = fields.Datetime()
    ks_cron_aus_interval_type = fields.Selection([('minutes', 'Minutes'),
                                                  ('hours', 'Hours'),
                                                  ('days', 'Days'),
                                                  ('weeks', 'Weeks'),
                                                  ('months', 'Months')], default='months')
    ks_database_name = fields.Char('Database Name', compute='_compute_count_of_woo_records')
    ks_current_user = fields.Char('Current User', compute='_compute_count_of_woo_records')

    @api.onchange('ks_global_discount_enable')
    def ks_onchange_global_discount_enable(self):
        """
        This function is used to reset global discount value on Gobal Discount Toggle button disable

        :return: none
        """
        for rec in self:
            if not rec.ks_global_discount_enable:
                rec.ks_global_discount = 0.0

    @api.constrains('ks_global_discount')
    def ks_depends_global_discount(self):
        """
        This function is used to Change the value of sale price in pricelist when global discount value is given and saved

        :return: none
        """
        for rec in self:
            if rec.ks_global_discount >= 100:
                raise ValidationError("Discount cannot exceed 99% !")
            elif rec.ks_global_discount < 0:
                raise ValidationError('Discount cannot be less than 0% !')
            if rec.ks_woo_pricelist_ids:
                pricelist = []
                for data in rec.ks_woo_pricelist_ids.search(
                        [('ks_onsale_pricelist', '=', False), ('ks_instance_id', '=', rec.id)]):
                    pricelist.append(data)
                for data in rec.ks_woo_pricelist_ids.search(
                        [('ks_onsale_pricelist', '=', True), ('ks_instance_id', '=', rec.id)]):
                    pricelist.append(data)
            else:
                pricelist = []
                pricelist.append(rec.ks_woo_pricelist)
                pricelist.append(rec.ks_woo_sale_pricelist)
            for record in pricelist:
                for data in record.item_ids:
                    self.ks_update_price_on_price_list_instance(record, data, rec)

    def ks_update_price_on_price_list_instance(self, price_list, record_exist, ks_instance):
        """
        This function is used to update prices on every pricelist created under current instance with the conversion rate

        :param price_list: current pricelist data
        :param record_exist: existing pricelist data in the database
        :param ks_instance: current instance data
        :return: none
        """
        if record_exist.product_id:
            if record_exist.product_id.ks_woo_product_type != 'variable':
                ks_woo_regular_price = record_exist.product_id.ks_woo_regular_price
            else:
                ks_woo_regular_price = record_exist.product_id.ks_woo_variant_reg_price
            if price_list.ks_onsale_pricelist == False:
                ks_price = float(ks_woo_regular_price or 0.0)
            else:
                if ks_instance.ks_global_discount_enable and ks_instance.ks_global_discount:
                    record_exist.ks_on_sale_price = True
                    ks_price = (float(ks_woo_regular_price or 0.0)) - (
                            (float(ks_woo_regular_price or 0.0) * ks_instance.ks_global_discount) / 100)
                    record_exist.product_id.list_price = ks_price
                elif ks_instance.ks_global_discount_enable and not ks_instance.ks_global_discount:
                    ks_price = 0.0
                    record_exist.product_id.list_price = ks_woo_regular_price
                else:
                    ks_price = float(record_exist.product_id.ks_woo_sale_price or 0.0)
                    record_exist.product_id.list_price = record_exist.product_id.ks_woo_sale_price if record_exist.product_id.ks_woo_sale_price else record_exist.product_id.ks_woo_regular_price
                if record_exist.currency_id.id == ks_instance.ks_woo_currency.id:
                    if record_exist.product_id.ks_woo_product_type != 'variable':
                        record_exist.product_id.ks_woo_sale_price = ks_price
                    else:
                        record_exist.product_id.ks_woo_variant_sale_price = ks_price
            ks_sale_price = float(record_exist.product_id.ks_woo_sale_price or 0.0)
            if price_list.ks_onsale_pricelist:
                record_exist.ks_on_sale_price = True
            if record_exist:
                if price_list.id == ks_instance.ks_woo_pricelist.id or price_list.id == ks_instance.ks_woo_sale_pricelist.id:
                    record_exist.fixed_price = ks_price
                else:
                    conversion_rate = price_list.currency_id.rate / ks_instance.ks_woo_pricelist.currency_id.rate
                    record_exist.fixed_price = ks_price * conversion_rate

                if ks_price < float(ks_woo_regular_price or 0.0) or (
                        ks_price == ks_sale_price and ks_sale_price != 0.0):
                    record_exist.ks_on_sale_price = True
                else:
                    record_exist.ks_on_sale_price = False
            else:
                price_list_item = {
                    'pricelist_id': price_list.id,
                    'applied_on': '0_product_variant',
                    'product_tmpl_id': record_exist.product_tmpl_id.id,
                    'product_id': record_exist.product_id.id,
                    'compute_price': 'fixed',
                    'ks_instance_id': record_exist.ks_woo_instance_id.id
                }
                if price_list.id == ks_instance.ks_woo_pricelist.id or price_list.id == ks_instance.ks_woo_sale_pricelist.id:
                    price_list_item.update({
                        'fixed_price': ks_price
                    })
                else:
                    conversion_rate = price_list.currency_id.rate / ks_instance.ks_woo_pricelist.currency_id.rate
                    computed_price = ks_price * conversion_rate
                    price_list_item.update({
                        'fixed_price': computed_price
                    })

                if ks_price == ks_sale_price and ks_sale_price != 0.0:
                    price_list_item.update({
                        'ks_on_sale_price': True,
                    })
                else:
                    price_list_item.update({
                        'ks_on_sale_price': False,
                    })
                price_list.item_ids.create(price_list_item)

    @api.onchange('ks_woo_multi_currency', 'ks_multi_currency_option')
    def ks_pricelist_domain(self):
        """
        This function is used to set domain for main currency on the change of multi currency option or multi currency field

        :return: domain for the main currency
        """
        self.ensure_one()
        if self.ks_multi_currency_option and len(self.ks_woo_multi_currency) > 0:
            return {
                'domain': {
                    'ks_woo_currency': [('id', 'in', self.ks_woo_multi_currency.ids)]
                }
            }
        elif not self.ks_multi_currency_option:
            return {
                'domain': {
                    'ks_woo_currency': [('id', 'in', self.env['res.currency'].search([]).ids)]
                }
            }
        return {
            'domain': {
                'ks_woo_currency': [('id', 'in', [])]
            }
        }

    def name_get(self):
        """
        Append the custom name in the drop down list
        :return: List of custom names
        """
        result = []
        for instance in self:
            name = "[" + instance.ks_id + "] - " + instance.ks_name
            result.append((instance.id, name))
        return result

    @api.model
    def create(self, values):
        """
        Creating default woocommerce values

        :param values: Data that has been changed or updated
        :return: Super Call
        """
        if values.get('ks_id', 'New') == 'New':
            values['ks_id'] = self.env['ir.sequence'].next_by_code(
                'ks.woocommerce.instances') or 'New'
        res = super(KsWooCommerceInstance, self).create(values)
        res.ks_import_order_state_config = [(0, 0, {'ks_woo_states': 'on-hold',
                                                    'ks_odoo_state': 'draft'}),
                                            (0, 0, {'ks_woo_states': 'pending',
                                                    'ks_odoo_state': 'sale'}),
                                            (0, 0, {'ks_woo_states': 'processing',
                                                    'ks_odoo_state': 'sale',
                                                    'ks_create_invoice': True,
                                                    'ks_set_invoice_state': 'paid'}),
                                            (0, 0, {'ks_woo_states': 'completed',
                                                    'ks_odoo_state': 'done',
                                                    'ks_create_invoice': True,
                                                    'ks_set_invoice_state': 'paid',
                                                    'ks_confirm_shipment': True})]
        res.ks_woo_fees = self.env.ref('ks_woocommerce.ks_woo_fees').id
        res.ks_woo_shipping = self.env.ref('ks_woocommerce.ks_woo_shipping_fees').id
        res.ks_woo_customer = self.env.ref('ks_woocommerce.ks_woo_guest_customers').id
        res.ks_manage_auto_job()
        return res

    @api.multi
    def write(self, values):
        """
        Manages the Automatic jobs

        :param values: Updated values from the form view
        :return: Super call
        """
        res = super(KsWooCommerceInstance, self).write(values)
        if self._context.get('ks_manage_auto_job', False):
            return res
        self.ks_manage_auto_job()
        return res

    @api.onchange('ks_multi_currency_option')
    def ks_main_currency_change(self):
        """
        This function is used to set domain for main currency on the change of multi currency option or multi currency field

        :return: none
        """
        for rec in self:
            if rec.ks_multi_currency_option:
                rec.ks_woo_currency = False
                rec.ks_woo_pricelist = False
            else:
                rec.ks_woo_multi_currency = [(5, 0, 0)]
                rec.ks_woo_pricelist_ids = [(5, 0, 0)]

    @api.depends('ks_woo_currency')
    def _ks_pricelist_on_currency_change(self):
        """
        This function is used create main pricelist

        :return: none
        """
        for rec in self:
            regular_pricelist_id = False
            if 'int' in str(type(rec.id)):
                if rec.ks_woo_currency:
                    regular_pricelist_id = self.env['product.pricelist'].search([('ks_instance_id', '=', rec.id),
                                                                                 ('currency_id', '=',
                                                                                  rec.ks_woo_currency.id),
                                                                                 ('ks_onsale_pricelist', '=',
                                                                                  False)])
                    onsale_pricelist_id = self.env['product.pricelist'].search([('ks_instance_id', '=', rec.id),
                                                                                ('currency_id', '=',
                                                                                 rec.ks_woo_currency.id),
                                                                                ('ks_onsale_pricelist', '=', True)])
                    if regular_pricelist_id:
                        rec.ks_woo_pricelist = regular_pricelist_id[0].id
                    else:
                        price_list_data = {
                            'name': rec.ks_name + ' ' + (rec.ks_woo_currency and rec.ks_woo_currency.name or '-') + ' Regular Pricelist',
                            'currency_id': rec.ks_woo_currency.id,
                            'company_id': rec.ks_company.id,
                            'ks_instance_id': rec.id,
                            'ks_onsale_pricelist': False,
                        }
                        if not self.env['product.pricelist'].search([('ks_instance_id', '=', rec.id),
                                                                                 ('currency_id', '=',
                                                                                  rec.ks_woo_currency.id),
                                                                                 ('ks_onsale_pricelist', '=',
                                                                                  False)]):
                            regular_pricelist_id = self.env['product.pricelist'].create(price_list_data)
                            rec.ks_woo_pricelist = regular_pricelist_id.id
                    if onsale_pricelist_id:
                        rec.ks_woo_sale_pricelist = onsale_pricelist_id[0].id
                    else:
                        price_list_data = {
                            'name': rec.ks_name + ' ' + (rec.ks_woo_currency and rec.ks_woo_currency.name or '-') + ' OnSale Pricelist',
                            'currency_id': rec.ks_woo_currency.id,
                            'company_id': rec.ks_company.id,
                            'ks_instance_id': rec.id,
                            'ks_onsale_pricelist': True,
                        }
                        if not self.env['product.pricelist'].search([('ks_instance_id', '=', rec.id),
                                                                                ('currency_id', '=',
                                                                                 rec.ks_woo_currency.id),
                                                                                ('ks_onsale_pricelist', '=', True)]):
                            pricelist_id = self.env['product.pricelist'].create(price_list_data)
                            rec.ks_woo_sale_pricelist = pricelist_id.id
            else:
                rec.ks_woo_pricelist = False
                rec.ks_woo_sale_pricelist = False
            if rec.ks_woo_multi_currency:
                # rec.ks_woo_pricelist_ids = rec.ks_woo_pricelist.search([('ks_instance_id', '=', rec.id)]).ids
                rec._ks_multi_pricelist_on_multi_currency_change()
            rec.ks_woo_pricelist = regular_pricelist_id.id if regular_pricelist_id else False

    @api.depends('ks_woo_multi_currency')
    def _ks_multi_pricelist_on_multi_currency_change(self):
        """
        This function is used create multi pricelist

        :return: none
        """
        for rec in self:
            if 'int' in str(type(rec.id)):
                if rec.ks_woo_multi_currency:
                    # rec.ks_woo_pricelist_ids = [(5, 0, 0)]
                    for currency_id in rec.ks_woo_multi_currency:
                        pricelist_id = self.env['product.pricelist'].search([('ks_instance_id', '=', rec.id),
                                                                             ('currency_id', '=', currency_id.id)])
                        if pricelist_id:
                            pricelist_price = []
                            for record in pricelist_id:
                                pricelist_price.append(record.id)
                                rec.ks_woo_pricelist_ids = [(4, record.id)]
                        else:
                            price_list_data = {
                                'name': rec.ks_name + ' ' + currency_id.name + ' Regular Pricelist',
                                'currency_id': currency_id.id,
                                'company_id': rec.ks_company.id,
                                'ks_instance_id': rec.id,
                                'ks_onsale_pricelist': False,
                            }
                            if not self.env['product.pricelist'].search([('ks_instance_id', '=', rec.id),
                                                                     ('currency_id', '=', currency_id.id),
                                                                     ('ks_onsale_pricelist', '=', False)]):
                                pricelist_id = self.env['product.pricelist'].create(price_list_data)
                                rec.ks_woo_pricelist_ids = [(4, pricelist_id.id)]
                            price_list_data = {
                                'name': rec.ks_name + ' ' + currency_id.name + ' OnSale Pricelist',
                                'currency_id': currency_id.id,
                                'company_id': rec.ks_company.id,
                                'ks_instance_id': rec.id,
                                'ks_onsale_pricelist': True,
                            }
                            if not self.env['product.pricelist'].search([('ks_instance_id', '=', rec.id),
                                                                  ('currency_id', '=', currency_id.id),
                                                                  ('ks_onsale_pricelist', '=', True)]):
                                pricelist_id = self.env['product.pricelist'].create(price_list_data)
                                rec.ks_woo_pricelist_ids = [(4, pricelist_id.id)]
            # else:
            #     rec.ks_woo_pricelist_ids = [(5, 0, 0)]

    def ks_manage_auto_job(self):
        """
        Updating values regarding all the woocommerce crons

        :return: None
        """
        if self.ks_instance_state != 'active':
            if self.ks_aio_cron_id.active:
                self.ks_aio_cron_id.active = False
            elif self.ks_aip_cron_id.active:
                self.ks_aip_cron_id.active = False
            elif self.ks_aus_cron_id.active:
                self.ks_aus_cron_id.active = False
            elif self.ks_auos_cron_id.active:
                self.ks_auos_cron_id.active = False
        if self.ks_auto_import_product:
            data = {
                'name': '[' + self.ks_id + '] - ' + self.ks_name + ': ' + 'WooCommerce Auto Product Import from Woo to Odoo (Do Not Delete)',
                'interval_number': self.ks_cron_ip_interval_number,
                'interval_type': self.ks_cron_ip_interval_type,
                'user_id': self.ks_cron_ip_schedule_user.id,
                'model_id': self.env.ref('product.model_product_template').id,
                'state': 'code',
                'active': self.ks_aip_cron_active_permission,
                'numbercall': -1,
                'ks_woo_instance_id': self.id,
                'ks_cron_type': 'auto import product'
            }
            if self.ks_aip_cron_id and self.ks_aip_update_permission:
                self.ks_aip_cron_id.write(data)
                self.ks_aip_update_permission = False
            if not self.ks_aip_cron_id:
                ks_aip_cron_id = self.env['ir.cron'].create(data)
                self.with_context({'ks_manage_auto_job': 'Do not run'}).write({'ks_aip_cron_id': ks_aip_cron_id.id})
                # self.ks_aio_cron_id = ks_aip_cron_id.id
                self.ks_aip_cron_id.write({'code': 'model.ks_auto_import_product(' + str(self.ks_aip_cron_id.id) + ')'})

        else:
            if self.ks_aip_cron_id.active:
                self.ks_aip_cron_id.active = False

        if self.ks_auto_update_stock:
            data = {
                'name': '[' + self.ks_id + '] - ' + self.ks_name + ': ' + 'WooCommerce Auto Product Stock Update from Odoo to Woo (Do Not Delete)',
                'interval_number': self.ks_cron_aus_interval_number,
                'interval_type': self.ks_cron_aus_interval_type,
                'user_id': self.ks_cron_aus_schedule_user.id,
                'model_id': self.env.ref('product.model_product_template').id,
                'state': 'code',
                'active': self.ks_aus_cron_active_permission,
                'numbercall': -1,
                'ks_woo_instance_id': self.id,
                'ks_cron_type': 'auto update stock'
            }
            if self.ks_aus_cron_id and self.ks_aus_update_permission:
                self.ks_aus_cron_id.write(data)
                self.ks_aus_update_permission = False
            if not self.ks_aus_cron_id:
                ks_aus_cron_id = self.env['ir.cron'].create(data)
                self.with_context({'ks_manage_auto_job': 'Do not run'}).write({'ks_aus_cron_id': ks_aus_cron_id.id})
                self.ks_aus_cron_id.code = 'model.ks_auto_update_stock(' + str(self.ks_aus_cron_id.id) + ')'
        else:
            if self.ks_aus_cron_id.active:
                self.ks_aus_cron_id.active = False

        if self.ks_auto_import_order:
            data = {
                'name': '[' + self.ks_id + '] - ' + self.ks_name + ': ' + 'WooCommerce Auto Order Import from Woo to Odoo (Do Not Delete)',
                'interval_number': self.ks_cron_aio_interval_number,
                'interval_type': self.ks_cron_aio_interval_type,
                'user_id': self.ks_cron_aio_schedule_user.id,
                'model_id': self.env.ref('sale.model_sale_order').id,
                'state': 'code',
                'active': self.ks_aio_cron_active_permission,
                'numbercall': -1,
                'ks_woo_instance_id': self.id,
                'ks_cron_type': 'auto import order',
            }
            if self.ks_aio_cron_id and self.ks_aio_update_permission:
                self.ks_aio_cron_id.write(data)
                self.ks_aio_update_permission = False
            if not self.ks_aio_cron_id:
                ks_aio_cron_id = self.env['ir.cron'].create(data)
                self.with_context({'ks_manage_auto_job': 'Do not run'}).write({'ks_aio_cron_id': ks_aio_cron_id.id})
                self.ks_aio_cron_id.code = 'model.ks_auto_import_order(' + str(self.ks_aio_cron_id.id) + ')'
        else:
            if self.ks_aio_cron_id.active:
                self.ks_aio_cron_id.active = False

        if self.ks_auto_update_order_status:
            data = {
                'name': '[' + self.ks_id + '] - ' + self.ks_name + ': ' + 'WooCommerce Auto Order Status Update from Odoo to Woo(Do Not Delete)',
                'interval_number': self.ks_cron_auos_interval_number,
                'interval_type': self.ks_cron_auos_interval_type,
                'user_id': self.ks_cron_auos_schedule_user.id,
                'model_id': self.env.ref('sale.model_sale_order').id,
                'state': 'code',
                'active': self.ks_auos_cron_active_permission,
                'numbercall': -1,
                'ks_woo_instance_id': self.id,
                'ks_cron_type': 'auto update order status'
            }
            if self.ks_auos_cron_id and self.ks_auos_update_permission:
                self.ks_auos_cron_id.write(data)
                self.ks_auos_update_permission = False
            if not self.ks_auos_cron_id:
                ks_auos_cron_id = self.env['ir.cron'].create(data)
                self.with_context({'ks_manage_auto_job': 'Do not run'}).write({'ks_auos_cron_id': ks_auos_cron_id.id})
                self.ks_auos_cron_id.code = 'model.ks_auto_update_order_status(' + str(self.ks_auos_cron_id.id) + ')'
        else:
            if self.ks_auos_cron_id.active:
                self.ks_auos_cron_id.active = False

    def ks_manage_auto_import_product_job(self):
        """
        Permission to manage the automatic Product import job on Button Click

        :return: Popup message wizard
        """
        self.ks_aip_update_permission = True
        self.ks_manage_auto_job()
        return self.env['ks.message.wizard'].ks_pop_up_message(names='Success',
                                                                   message='Auto Import Product Cron has been Successfully updated')

    def ks_manage_auto_import_order_job(self):
        """
        Permission to manage the automatic Order import job on Button Click

        :return: Popup message wizard
        """
        self.ks_aio_update_permission = True
        self.ks_manage_auto_job()
        return self.env['ks.message.wizard'].ks_pop_up_message(names='Success',
                                                                   message='Auto Import Order Cron has been Successfully updated')

    def ks_manage_auto_update_order_status_job(self):
        """
        Permission to manage the automatic Order Status export job on Button Click

        :return: Popup message wizard
        """
        self.ks_auos_update_permission = True
        self.ks_manage_auto_job()
        return self.env['ks.message.wizard'].ks_pop_up_message(names='Success',
                                                                   message='Auto Update Order Status Cron has been Successfully updated')

    def ks_manage_auto_update_stock_job(self):
        """
        Permission to manage the automatic Product stock Update export job on Button Click

        :return: Popup message wizard
        """
        self.ks_aus_update_permission = True
        self.ks_manage_auto_job()
        return self.env['ks.message.wizard'].ks_pop_up_message(names='Success',
                                                                   message='Auto Update Stock Cron has been Successfully updated')

    def _compute_count_of_woo_records(self):
        """
        Count of Orders, Products, Coupons, Customers for dashboard

        :return: None
        """
        for rec in self:
            search_query = [('ks_woo_instance_id', '=', rec.id), ('ks_woo_id', '!=', False)]
            rec.ks_database_name = request.session.db
            rec.ks_current_user = self.env.user.id
            rec.ks_woo_count_orders = rec.env['sale.order'].search_count(search_query)
            rec.ks_woo_count_products = rec.env['product.template'].search_count(search_query)
            rec.ks_woo_count_coupons = rec.env['ks.woo.coupon'].search_count(search_query)
            rec.ks_woo_count_customers = rec.env['res.partner'].search_count(search_query)

    def open_form_action(self):
        """
        Open the Operation Form View in the wizard

        :return: The form view
        """
        view = self.env.ref('ks_woocommerce.ks_woo_instance_operation_form_view')
        return {
            'type': 'ir.actions.act_window',
            'name': 'WooCommerce Operations',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'res_model': 'ks.woo.instance.operation',
            'view_mode': 'form',
            'context': {'default_ks_woo_instances': [(6, 0, [self.id])], 'default_woo_instance': True},
            'target': 'new',
        }

    def ks_open_woo_orders(self):
        """
        Open the view regarding the Sales Order with respective to Instance

        :return: The view
        """
        action = self.env.ref('ks_woocommerce.action_woocommerce_sale_order').read()[0]
        action['domain'] = [('ks_woo_instance_id', '=', self.id)]
        return action

    def ks_open_woo_products(self):
        """
        Open the view regarding the Products with respective to Instance

        :return: The view
        """
        action = self.env.ref('ks_woocommerce.action_woocommerce_product_templates').read()[0]
        action['domain'] = [('ks_woo_instance_id', '=', self.id)]
        return action

    def ks_open_woo_coupons(self):
        """
        Open the view regarding the Coupons with respective to Instance

        :return: The view
        """
        action = self.env.ref('ks_woocommerce.action_woocommerce_coupons').read()[0]
        action['domain'] = [('ks_woo_instance_id', '=', self.id)]
        return action

    def ks_open_woo_customers(self):
        """
        Open the view regarding the Customers with respective to Instance

        :return: The view
        """
        action = self.env.ref('ks_woocommerce.action_woocommerce_res_partner').read()[0]
        action['domain'] = [('ks_woo_instance_id', '=', self.id)]
        return action

    def ks_open_woo_configuration(self):
        """
        Open the Woocommerce Configuration wizard

        :return: The form view
        """
        return {
            'type': 'ir.actions.act_window',
            'name': 'WooCommerce Operations',
            'view': 'form',
            'res_id': self.id,
            'res_model': 'ks.woocommerce.instances',
            'view_mode': 'form',
        }

    def ks_open_instance_logs(self):
        """
        Redirect to the Instance log form view

        :return: The tree view
        """
        action = self.env.ref('ks_woocommerce.action_woocommerce_logs').read()[0]
        action['domain'] = [('ks_woo_instance_id', '=', self.id)]
        return action

    def ks_connect_to_woo_instance(self):
        """
        Establishing Connection with the Woocommerce

        :return: Popup message wizard
        """
        try:
            wcapi = self.ks_api_authentication()
            if wcapi.get("").status_code == 200:
                message = 'Connection Successful'
                names = 'Success'
                self.ks_instance_connected = True
                self.ks_instance_state = 'connected'
            else:
                message = str(wcapi.get("").status_code) + ': ' + eval(wcapi.get("").text).get('message') if len(
                    wcapi.get("").text.split(
                        "woocommerce_rest_authentication_error")) > 1 else 'Please enter the Valid WooCommerce Store URL'
                if message == '401: Consumer key is invalid.':
                    message = "Customer Key is Invalid"
                if message == '401: Invalid signature - provided signature does not match.':
                    message = "Customer Secret Key is Invalid"
                names = 'Error'
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_status='success' if wcapi.get("").status_code in [200,
                                                                                                              201] else 'failed',
                                                         ks_type='system_status',
                                                         ks_woo_instance_id=self,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='connection',
                                                         response='Connection successful' if wcapi.get("").status_code
                                                                                             in [200, 201] else message if message=='Please enter the Valid WooCommerce Store URL' else wcapi.get("").text)
        except ConnectionError:
            raise ValidationError(
                "Couldn't Connect the instance !! Please check the network connectivity or the configuration or Store "
                "URL "
                " parameters are "
                "correctly set.")
        except Exception as e:
            names = 'Error'
            message = 'Please enter the Valid WooCommerce Store URL' if 'http' in str(
                e) else e
            self.env['ks.woo.sync.log'].ks_exception_log(record='',
                                                         type='system_status',
                                                         operation_type="connection",
                                                         instance_id=self,
                                                         operation="odoo_to_woo",
                                                         exception=e)
        return self.env['ks.message.wizard'].ks_pop_up_message(names=names, message=message)

    def ks_activate_instance(self):
        """
        Activating the Woocommerce Instance

        :return: Popup message wizard
        """
        if self.ks_instance_connected and self.ks_instance_state == 'connected':
            self.ks_instance_state = 'active'
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_status='success',
                                                         ks_type='system_status',
                                                         ks_woo_instance_id=self,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='connection',
                                                         response='Activation successful')
            return self.env['ks.message.wizard'].ks_pop_up_message(names='Success',
                                                                   message='Instance Activated')

    def ks_deactivate_instance(self):
        """
        Deactivating the Woocommerce Instance

        :return: Popup message wizard
        """
        if self.ks_instance_connected and self.ks_instance_state == 'active':
            self.ks_instance_state = 'deactivate'
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_status='success',
                                                         ks_type='system_status',
                                                         ks_woo_instance_id=self,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='connection',
                                                         response='Deactivation successful')
            return self.env['ks.message.wizard'].ks_pop_up_message(names='Success',
                                                                   message='Instance Deactivated')

    def ks_api_authentication(self):
        """
        Preparing the API Data

        :return: Prepared data
        """
        wcapi = WCAPI(
            url=self.ks_woo_store_url,
            consumer_key=self.ks_customer_key,
            consumer_secret=self.ks_customer_secret,
            wp_api=True,
            version=self.ks_wc_version,
            verify_ssl=self.ks_verify_ssl,
            timeout=50,
            query_string_auth = self.ks_auth
        )
        return wcapi

    def ks_store_record_after_export(self, odoo_record, woo_record):
        """
        Storing the record after exporting to Woocommerce

        :param odoo_record: Odoo Side Record
        :param woo_record: Woocommerce Side Record
        :return: None
        """
        odoo_record.ks_woo_id = woo_record.get('id') or ''
        if woo_record.get('date_modified'):
            odoo_record.ks_date_updated = datetime.strptime(
                (woo_record.get('date_modified') or False).replace('T',
                                                                   ' '),
                DEFAULT_SERVER_DATETIME_FORMAT)
        if woo_record.get('date_created'):
            odoo_record.ks_date_created = datetime.strptime(
                (woo_record.get('date_created') or False).replace('T',
                                                                  ' '),
                DEFAULT_SERVER_DATETIME_FORMAT)

    def ks_store_record_after_import(self, odoo_record, woo_record, instance):
        """
        Storing Instance Id after exporting to Woocommerce

        :param odoo_record: Odoo side Record
        :param woo_record: Woocommerce side Record
        :param instance: Woocommerce Instance Id
        :return: None
        """
        odoo_record.ks_woo_id = woo_record.get('id') or ''
        odoo_record.ks_woo_instance_id = instance.id

    def ks_instance_status_error(self):
        """
        Returning the Popup message wizard

        :return: Popup message wizard
        """
        return self.env['ks.message.wizard'].ks_pop_up_message(names='Error',
                                                               message="WooCommerce instance must be in "
                                                                       "active state to perform operations.")


class KsWooOrderStatus(models.Model):
    _name = 'ks.woocommerce.status'
    _description = 'WooCommerce Order Status'

    ks_woo_states = fields.Selection([('on-hold', 'On-hold'), ('pending', 'Pending'),
                                      ('processing', 'Processing'), ('completed', 'Completed')], readonly=True,
                                     string='Woo State')
    ks_sync = fields.Boolean('Sync')
    ks_odoo_state = fields.Selection([('draft', 'Quotation'), ('sale', 'Sale Order'), ('done', 'Done')],
                                     string='Odoo state')
    ks_create_invoice = fields.Boolean(string='Create Invoice')
    ks_set_invoice_state = fields.Selection([('draft', 'Draft'), ('open', 'Open'), ('paid', 'Paid')],
                                            string='Set Invoice state')
    ks_confirm_shipment = fields.Boolean(string='Confirm Shipment')
    ks_instance_id = fields.Many2one('ks.woocommerce.instances', string="WooCommerce Instance")

    @api.onchange('ks_odoo_state')
    def _onchange_ks_odoo_state(self):
        """
        Changing state of Invoice, shipment on the change of Odoo State
        :return: None
        """
        if self.ks_odoo_state == 'draft':
            self.ks_create_invoice = self.ks_set_invoice_state = self.ks_confirm_shipment = False

    @api.onchange('ks_create_invoice')
    def _onchnage_ks_create_invoice(self):
        """
        Changing the Invoice State
        :return: None
        """
        if self.ks_create_invoice:
            if self.ks_odoo_state == 'draft':
                raise ValidationError('You can not create invoice if order is in Quotation State !')
        else:
            self.ks_set_invoice_state = False
