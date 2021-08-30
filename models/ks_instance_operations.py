# -*- coding: utf-8 -*-

import logging
from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from requests.exceptions import ConnectionError

_logger = logging.getLogger(__name__)


class KsWooInstanceOperation(models.TransientModel):
    _name = "ks.woo.instance.operation"
    _description = "WooCommerce Instance Operations"

    @api.model
    def _get_default_ks_woo_instances_ids(self):
        """
        :return: All the active Woo Instance Id for multiple instances operation
        """
        instance_ids = self.env['ks.woocommerce.instances'].search([('ks_instance_state', '=', 'active')]).ids
        return [(6, 0, instance_ids)]

    ks_woo_instances = fields.Many2many('ks.woocommerce.instances', default=_get_default_ks_woo_instances_ids,
                                        string="Woo Instance", help="""WooCommerce Instance: Ths instance of woocomerce to which this 
                                                     customer belongs to.""")
    ks_sync_orders = fields.Boolean(string="Sync Orders")
    ks_sync_customers = fields.Boolean(string="Sync Customers")
    ks_sync_coupons = fields.Boolean(string="Sync Coupons")
    ks_sync_products = fields.Boolean(string="Sync Products")
    ks_sync_attributes = fields.Boolean(string="Sync Attributes")
    ks_sync_product_tags = fields.Boolean(string="Sync Tags")
    ks_sync_product_category = fields.Boolean(string="Sync Category")
    ks_sync_payment_gateways = fields.Boolean(string="Sync Payment Gateway")
    ks_publish_products = fields.Boolean(string="Publish Product")
    ks_unpublish_products = fields.Boolean(string="Unpublish Product")
    ks_update_customers = fields.Boolean(string="Export/Update Customers")
    ks_update_products = fields.Boolean(string="Export/Update Products")
    ks_update_coupons = fields.Boolean(string="Export/Update Coupons")
    ks_update_attributes = fields.Boolean(string="Export/Update Attributes")
    ks_update_category = fields.Boolean(string="Export/Update Categories")
    ks_update_tags = fields.Boolean(string="Export/Update Tags")
    ks_update_order_status = fields.Boolean(string="Export/Update Order status")
    ks_update_stock = fields.Boolean(string="Export/Update Stock")
    ks_import_stock = fields.Boolean(string="Sync Stock")
    ks_sync_all_w2o = fields.Boolean(string="Want to perform all the tasks?")
    ks_date_filter = fields.Boolean(string="Date Filter")
    ks_date_from = fields.Date(string="From Date")
    ks_date_to = fields.Date(string="To Date")
    ks_date_filter_info = fields.Char(default="[Date filter works on Products, Sale Orders and Customers.]",
                                      readonly=True)

    @api.onchange('ks_date_filter')
    def ks_maintain_dates(self):
        """
        Sets Date From and Date To to False for the filter

        :return: None
        """
        if not self.ks_date_filter:
            self.ks_date_to = False
            self.ks_date_from = False

    @api.onchange('ks_date_to')
    def _onchange_ks_date_to(self):
        """
        Validating the fields of Date From and Date To.

        :return: None
        """
        if self.ks_date_to and self.ks_date_to < self.ks_date_from:
            self.ks_date_from = self.ks_date_to

    @api.onchange('ks_sync_all_w2o')
    def ks_check_all_w2o(self):
        """
        Assigning the value to all the Operation to perform.

        :return: None
        """
        all_sync = True if self.ks_sync_all_w2o else False
        self.ks_sync_products = self.ks_sync_orders = self.ks_sync_coupons = self.ks_sync_customers = \
            self.ks_sync_attributes = self.ks_sync_product_tags = self.ks_sync_product_category = \
            self.ks_sync_payment_gateways = all_sync

    def ks_execute_operation(self):
        """
        This will execute all the operations selection according to the instance.

        :return: A successful message after performing all operations
        """
        if self.ks_sync_orders or self.ks_sync_customers or self.ks_sync_coupons or self.ks_sync_products or \
                self.ks_sync_attributes or self.ks_sync_product_tags or self.ks_sync_product_category or \
                self.ks_sync_payment_gateways or self.ks_publish_products or self.ks_unpublish_products or \
                self.ks_update_customers or self.ks_update_products or self.ks_update_coupons or \
                self.ks_update_attributes or self.ks_update_category or self.ks_update_tags or \
                self.ks_update_order_status or self.ks_update_stock or self.ks_import_stock:
            for each_instance in self.ks_woo_instances:
                if each_instance.ks_instance_state == 'active':
                    try:
                        wcapi = each_instance.ks_api_authentication()
                        if wcapi.get("").status_code in [200, 201]:
                            if self.ks_sync_attributes:
                                _logger.info('Attribute Syncing start For WooCommerce Instance [%s -(%s)]'
                                             , each_instance.ks_name, each_instance.id)
                                self.env['ks.woo.queue.jobs'].ks_sync_product_attribute_woocommerce_to_queue(
                                    wcapi=wcapi, instance_id=each_instance)
                            if self.ks_sync_product_tags:
                                _logger.info('Tag Syncing start For WooCommerce Instance [%s -(%s)]'
                                             , each_instance.ks_name, each_instance.id)
                                self.env['ks.woo.queue.jobs'].ks_sync_product_tag_to_queue(
                                    wcapi=wcapi,
                                    instance_id=each_instance)
                            if self.ks_sync_product_category:
                                _logger.info('Category Syncing start For WooCommerce Instance [%s -(%s)]'
                                             , each_instance.ks_name, each_instance.id)
                                self.env['ks.woo.queue.jobs'].ks_sync_product_category_to_queue(wcapi=wcapi,
                                                                                                instance_id=each_instance)
                            if self.ks_sync_coupons:
                                _logger.info('Coupon Syncing start For WooCommerce Instance [%s -(%s)]'
                                             , each_instance.ks_name, each_instance.id)
                                self.env['ks.woo.queue.jobs'].ks_sync_coupon_from_woo_to_queue(wcapi=wcapi,
                                                                                               instance_id=each_instance)
                            if self.ks_sync_products:
                                _logger.info('Product Syncing start For WooCommerce Instance [%s -(%s)]'
                                             , each_instance.ks_name, each_instance.id)
                                self.env['ks.woo.queue.jobs'].with_context({'ks_date_filter': self.ks_date_filter,
                                                                            'ks_date_from': self.ks_date_from,
                                                                            'ks_date_to': self.ks_date_to}).ks_sync_product_woocommerce_in_queue(
                                    wcapi=wcapi,
                                    instance_id=each_instance)
                            if self.ks_import_stock:
                                _logger.info('Stock importing start For WooCommerce Instance [%s -(%s)]'
                                             , each_instance.ks_name, each_instance.id)
                                self.env['ks.woo.queue.jobs'].ks_import_stock_woocommerce_in_queue(
                                    wcapi=wcapi,
                                    instance_id=each_instance)
                            if self.ks_update_category:
                                _logger.info('Updating the categories on WooCommerce Instance [%s -(%s)]'
                                             , each_instance.ks_name, each_instance.id)
                                category_records = self.env['product.category'].search(
                                    [('ks_woo_instance_id', '=', each_instance.id)])
                                self.env['ks.woo.queue.jobs'].ks_update_product_category_to_queue(
                                    category_records=category_records,
                                    instance_id=each_instance)

                            if self.ks_sync_customers:
                                _logger.info('Customer Syncing start For WooCommerce Instance [%s -(%s)]'
                                             , each_instance.ks_name, each_instance.id)
                                self.env['ks.woo.queue.jobs'].with_context({'ks_date_filter': self.ks_date_filter,
                                                                            'ks_date_from': self.ks_date_from,
                                                                            'ks_date_to': self.ks_date_to}).ks_sync_customer_woocommerce_in_queue(wcapi=wcapi,
                                                                                                    instance_id=each_instance)
                            if self.ks_sync_payment_gateways:
                                _logger.info('Payment Gateway Syncing start For WooCommerce Instance [%s -(%s)]'
                                             , each_instance.ks_name, each_instance.id)
                                self.env['ks.woo.queue.jobs'].ks_sync_payment_gateway_in_queue(
                                    wcapi=wcapi,
                                    instance_id=each_instance)
                            if self.ks_sync_orders:
                                _logger.info('Orders Syncing start For WooCommerce Instance [%s -(%s)]'
                                             , each_instance.ks_name, each_instance.id)
                                self.env['ks.woo.queue.jobs'].with_context({'ks_date_filter': self.ks_date_filter,
                                                                            'ks_date_from': self.ks_date_from,
                                                                            'ks_date_to': self.ks_date_to}).ks_sync_sale_order_to_queue(wcapi=wcapi,
                                                                                          instance_id=each_instance)
                            if self.ks_unpublish_products or self.ks_publish_products:
                                if self.ks_publish_products:
                                    _logger.info('Publishing the products For WooCommerce Instance [%s -(%s)]'
                                                 , each_instance.ks_name, each_instance.id)
                                elif self.ks_unpublish_products:
                                    _logger.info('UnPublishing the products For WooCommerce Instance [%s -(%s)]'
                                                 , each_instance.ks_name, each_instance.id)
                                product_records = self.env['product.template'].search(
                                    [('ks_woo_instance_id', '=', each_instance.id),
                                     ('ks_woo_id', '!=', False)])
                                if product_records:
                                    product_records_data = self.env['product.template'].ks_publish_unpublish_data(
                                        product_records,
                                        op_type='unpublish' if
                                        self.ks_unpublish_products else
                                        'publish')
                                    if wcapi.get("").status_code in [200, 201]:
                                        batch_size = 25
                                        if len(product_records_data['update']) >= batch_size:
                                            no_of_batches = len(product_records_data['update']) // batch_size
                                            for each_rec in range(0, no_of_batches + 1):
                                                batch_product_records = product_records_data['update'][
                                                                        0 + (batch_size * each_rec):batch_size + (
                                                                                batch_size * each_rec)]
                                                batch_product_records_data = {'update': batch_product_records}
                                                woo_response = wcapi.post("products/batch", batch_product_records_data)

                                                self.ks_batch_update_response(woo_response, each_instance,
                                                                              self.ks_unpublish_products)
                                                if woo_response.status_code in [200, 201]:
                                                    product_records.write(
                                                        {'ks_woo_status': False if self.ks_unpublish_products else True})
                                                else:
                                                    self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                                                                 ks_status='success' if wcapi.get(
                                                                                                     "").status_code in [
                                                                                                                            200,
                                                                                                                            201] else 'failed',
                                                                                                 ks_type='system_status',
                                                                                                 ks_woo_instance_id=each_instance,
                                                                                                 ks_operation='odoo_to_woo',
                                                                                                 ks_operation_type='connection',
                                                                                                 response='Connection successful' if wcapi.get(
                                                                                                     "").status_code in [
                                                                                                                                         200,
                                                                                                                                         201] else wcapi.get(
                                                                                                     "").text)

                                        else:
                                            woo_response = wcapi.post("products/batch", product_records_data)
                                            self.ks_batch_update_response(woo_response, each_instance,
                                                                          self.ks_unpublish_products)
                                            if woo_response.status_code in [200, 201]:
                                                product_records.write(
                                                    {'ks_woo_status': False if self.ks_unpublish_products else True})
                                            else:
                                                self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                                                             ks_status='success' if wcapi.get(
                                                                                                 "").status_code in [200,
                                                                                                                     201] else 'failed',
                                                                                             ks_type='system_status',
                                                                                             ks_woo_instance_id=each_instance,
                                                                                             ks_operation='odoo_to_woo',
                                                                                             ks_operation_type='connection',
                                                                                             response='Connection successful' if wcapi.get(
                                                                                                 "").status_code in [200,
                                                                                                                     201] else wcapi.get(
                                                                                                 "").text)
                                else:
                                    response = 'Products unpublished operation failed as there is no product to unpublish ' if self.ks_unpublish_products else 'Products published operation failed as there is no product to publish'
                                    self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                                                 ks_status='failed',
                                                                                 ks_type='product',
                                                                                 ks_woo_instance_id=each_instance,
                                                                                 ks_operation='odoo_to_woo',
                                                                                 ks_operation_type='batch_update',
                                                                                 response=response)
                            if self.ks_update_stock:
                                _logger.info('Updating Stock of the products on WooCommerce Instance [%s -(%s)]'
                                             , each_instance.ks_name, each_instance.id)
                                product_stock_records = self.env['product.template'].search(
                                    [('ks_woo_instance_id', '=', each_instance.id),
                                     ('ks_woo_id', '!=', False)])
                                self.env['ks.woo.queue.jobs'].ks_update_product_stock_to_queue(product_stock_records,
                                                                                               each_instance)
                                # self.env['product.template'].ks_update_product_stock(each_instance, wcapi)
                            if self.ks_update_products:
                                _logger.info('Updating the products on WooCommerce Instance [%s -(%s)]'
                                             , each_instance.ks_name, each_instance.id)
                                products_records = self.env['product.template'].search(
                                    [('ks_woo_instance_id', '=', each_instance.id), ('ks_to_be_export', '!=', False)])
                                self.env['ks.woo.queue.jobs'].ks_update_product_to_queue(
                                    products_records=products_records,
                                    instance_id=each_instance)

                            if self.ks_update_attributes:
                                _logger.info('Updating the attributes on WooCommerce Instance [%s -(%s)]'
                                             , each_instance.ks_name, each_instance.id)
                                attributes_records = self.env['product.attribute'].search(
                                    [('ks_woo_instance_id', '=', each_instance.id), ('ks_woo_id', '!=', -1)])
                                self.env['ks.woo.queue.jobs'].ks_update_product_attribute_to_queue(
                                    attributes_records=attributes_records,
                                    instance_id=each_instance)

                            if self.ks_update_tags:
                                _logger.info('Updating the tags on WooCommerce Instance [%s -(%s)]'
                                             , each_instance.ks_name, each_instance.id)
                                tags_records = self.env['ks.woo.product.tag'].search(
                                    [('ks_woo_instance_id', '=', each_instance.id)])
                                self.env['ks.woo.queue.jobs'].ks_update_product_tag_to_queue(tags_records=tags_records,
                                                                                             instance_id=each_instance)

                            if self.ks_update_coupons:
                                _logger.info('Updating the coupons on WooCommerce Instance [%s -(%s)]'
                                             , each_instance.ks_name, each_instance.id)
                                coupons_records = self.env['ks.woo.coupon'].search(
                                    [('ks_woo_instance_id', '=', each_instance.id)])
                                self.env['ks.woo.queue.jobs'].ks_update_coupon_to_queue(coupons_records=coupons_records,
                                                                                        instance_id=each_instance)

                            if self.ks_update_customers:
                                _logger.info('Updating the customers on WooCommerce Instance [%s -(%s)]'
                                             , each_instance.ks_name, each_instance.id)
                                customer_records = self.env['res.partner'].search(
                                    [('ks_woo_instance_id', '=', each_instance.id)])
                                self.env['ks.woo.queue.jobs'].ks_update_customer_woocommerce_in_queue(
                                    customers_records=customer_records,
                                    instance_id=each_instance)
                            if self.ks_update_order_status:
                                _logger.info('Updating the Saler Order status for WooCommerce Instance [%s -(%s)]'
                                             , each_instance.ks_name, each_instance.id)
                                self.env['sale.order'].ks_update_order_status(each_instance, wcapi)
                            cron_record = self.env.ref('ks_woocommerce.ks_ir_cron_job_process')
                            if cron_record:
                                next_exc_time = datetime.now()
                                cron_record.sudo().write({'nextcall': next_exc_time})
                        else:
                            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                                         ks_status='success' if wcapi.get(
                                                                             "").status_code in [
                                                                                                    200,
                                                                                                    201] else 'failed',
                                                                         ks_type='system_status',
                                                                         ks_woo_instance_id=each_instance,
                                                                         ks_operation='odoo_to_woo',
                                                                         ks_operation_type='connection',
                                                                         response='Connection successful' if wcapi.get(
                                                                             "").status_code in [200,
                                                                                                 201] else wcapi.get(
                                                                             "").text)
                    except ConnectionError:
                        self.env['ks.woo.sync.log'].ks_connection_error_log(each_instance, type='system_status',
                                                                            operation=False)
                    except Exception as e:
                        self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="system_status",
                                                                     operation_type=False, instance_id=each_instance,
                                                                     operation=False, exception=e)
                else:
                    return self.env['ks.message.wizard'].ks_pop_up_message(names='Error',
                                                                           message="WooCommerce instance must be in "
                                                                                   "active state to perform operations.")
        else:
            raise ValidationError('Please select an operation to Execute..!')

        return self.env['ks.message.wizard'].ks_pop_up_message(names='Success', message="WooCommerce Operations has "
                                                                                        "been performed, Please refer "
                                                                                        "logs for further details.")

    def ks_batch_update_response(self, woo_response, each_instance, ks_unpublish_products=False):
        """
        Published and UnPublished product on the import functionality

        :param woo_response: Response from the API
        :param each_instance: Current Instance record
        :param ks_unpublish_products: List of Unpublish Products
        :return: None
        """
        if woo_response.status_code in [200, 201]:
            woo_records = woo_response.json()
            for each_rec in woo_records.get('update'):
                if each_rec.get('error'):
                    ks_status = "failed"
                    ks_woo_id = each_rec.get('id')
                    response = 'Products unpublished operation for Woo Id [' + str(each_rec.get(
                        'id')) + '] failed due to ' if ks_unpublish_products else 'Products published operation for Woo Id [' + str(
                        each_rec.get('id')) + '] failed due to ' + each_rec.get('error').get('message')
                else:
                    ks_status = "success"
                    ks_woo_id = each_rec.get('id')
                    response = 'Product with Woo Id [' + str(each_rec.get(
                        'id')) + '] has been unpublished' if ks_unpublish_products else 'Product with Woo Id [' + str(
                        each_rec.get('id')) + '] has been published'
                self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=ks_woo_id,
                                                             ks_status=ks_status,
                                                             ks_type='product',
                                                             ks_woo_instance_id=each_instance,
                                                             ks_operation='odoo_to_woo',
                                                             ks_operation_type='batch_update',
                                                             response=response)
        else:
            ks_status = "failed"
            ks_woo_id = False
            response = 'Products unpublished operation failed due to ' if ks_unpublish_products else 'Products published operation failed due to ' + eval(
                woo_response.text).get('message')
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=ks_woo_id,
                                                         ks_status=ks_status,
                                                         ks_type='product',
                                                         ks_woo_instance_id=each_instance,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='batch_update',
                                                         response=response)

    def ks_update_stock_wizard(self):
        """
        Update stock Wizard load

        :return: Wizard pop-up
        """
        # Open wizard to update inventory/ inventory adjustment
        view = self.env.ref('ks_woocommerce.ks_update_stock_at_once_wizrad')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Update Stock',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'res_model': 'ks.update.stock.at.once',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_ks_instance_id': self.ks_woo_instances.id},
        }