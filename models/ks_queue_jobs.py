import json

from odoo import models, fields
from requests.exceptions import ConnectionError
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class KsQueueManager(models.TransientModel):
    _name = 'ks.woo.queue.jobs'
    _description = 'This is used to Sync all the record in queues'
    _rec_name = 'ks_name'
    _order = 'id desc'

    ks_model = fields.Selection([('product_template', 'Product Template'), ('product_product', 'Product Variants'),
                                 ('sale_order', 'Sale Order'), ('customer', 'Customer'), ('coupon', 'Coupon'),
                                 ('attribute', 'Attributes'), ('tag', 'Tags'), ('category', 'Category'),
                                 ('stock', 'Stock'), ('payment_gateway', 'Payment Gateway')], string='Model')
    ks_name = fields.Char('Name')
    ks_type = fields.Selection([('import', 'Import'), ('export', 'Export')], string="Operation")
    state = fields.Selection([('new', 'New'), ('progress', 'In Progress'), ('done', 'Done'), ('failed', 'Failed')],
                             string='State')
    ks_woo_id = fields.Char('WooCommerce ID')
    ks_instance_id = fields.Many2one('ks.woocommerce.instances', 'Woo Instance')
    ks_data = fields.Text('WooCommerce Data')
    ks_operation = fields.Selection([('woo_to_odoo', 'Woo to Odoo'), ('odoo_to_woo', 'Odoo to Woo')],
                                    string="Operation Performed")
    ks_record_id = fields.Integer('Record ID')

    def ks_process_queue_jobs(self):
        """
        Processing the Queue Jobs

        :return: None
        """
        if not self.id:
            self = self.search([('state', 'in', ['new', 'failed', 'progress'])])
        for record in self:
            wcapi = record.ks_instance_id.ks_api_authentication()
            if record.ks_model == 'product_template':
                record.state = 'progress'
                record.env.cr.commit()
                try:
                    product_record = False
                    if record.ks_operation == 'odoo_to_woo':
                        product_record = record.env['product.template'].browse(record.ks_record_id)
                        product_record.ks_update_product_to_woo()
                    else:
                        product_data = json.loads(record.ks_data)
                        record.env['product.template'].ks_mangae_woo_product(product_data, wcapi, record.ks_instance_id)
                    record.state = 'done'
                    if product_record:
                        record.ks_woo_id = product_record.ks_woo_id
                    self.env.cr.commit()
                except Exception as e:
                    record.state = 'failed'
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=record.ks_woo_id,
                        ks_status='failed',
                        ks_type='product',
                        ks_woo_instance_id=record.ks_instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='create',
                        response=e,
                    )
            elif record.ks_model == 'customer':

                record.state = 'progress'
                record.env.cr.commit()
                try:
                    customer_record = False
                    if record.ks_operation == 'odoo_to_woo':
                        customer_record = record.env['res.partner'].browse(record.ks_record_id)
                        customer_record.ks_update_customer_to_woo()
                    else:
                        customer_data = json.loads(record.ks_data)
                        record.env['res.partner'].ks_manage_customer_woo_data(record.ks_instance_id, customer_data)
                    record.state = 'done'
                    if customer_record:
                        record.ks_woo_id = customer_record.ks_woo_id
                    self.env.cr.commit()
                except Exception as e:
                    record.state = 'failed'
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=record.ks_woo_id,
                        ks_status='failed',
                        ks_type='customer',
                        ks_woo_instance_id=record.ks_instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='create',
                        response=e,
                    )
            elif record.ks_model == 'tag':

                record.state = 'progress'
                record.env.cr.commit()
                try:
                    tag_record = False
                    if record.ks_operation == 'odoo_to_woo':
                        tag_record = record.env['ks.woo.product.tag'].browse(record.ks_record_id)
                        tag_record.ks_update_product_tag_to_woo()
                    else:
                        product_tag_data = json.loads(record.ks_data)
                        record.env['ks.woo.product.tag'].ks_manage_product_tags(product_tag_data, record.ks_instance_id)
                    record.state = 'done'
                    if tag_record:
                        record.ks_woo_id = tag_record.ks_woo_id
                    self.env.cr.commit()
                except Exception as e:
                    record.state = 'failed'
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=record.ks_woo_id,
                        ks_status='failed',
                        ks_type='tags',
                        ks_woo_instance_id=record.ks_instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='create',
                        response=e,
                    )
            elif record.ks_model == 'coupon':
                record.state = 'progress'
                record.env.cr.commit()
                try:
                    coupon_record = False
                    if record.ks_operation == 'odoo_to_woo':
                        coupon_record = record.env['ks.woo.coupon'].browse(record.ks_record_id)
                        coupon_record.ks_update_coupon_to_woo()
                    else:
                        coupons_data = json.loads(record.ks_data)
                        record.env['ks.woo.coupon'].ks_manage_coupon_woo_data(record.ks_instance_id, coupons_data)
                    record.state = 'done'
                    if coupon_record:
                        record.ks_woo_id = coupon_record.ks_woo_id
                    self.env.cr.commit()
                except Exception as e:
                    record.state = 'failed'
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=record.ks_woo_id,
                        ks_status='failed',
                        ks_type='tags',
                        ks_woo_instance_id=record.ks_instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='create',
                        response=e,
                    )
            elif record.ks_model == 'payment_gateway':
                payment_gateway_data = json.loads(record.ks_data)
                record.state = 'progress'
                record.env.cr.commit()
                try:
                    record.env['ks.woo.payment.gateway'].ks_manage_payment_gateway(record.ks_instance_id,
                                                                                   payment_gateway_data)
                    record.state = 'done'
                    self.env.cr.commit()
                except Exception as e:
                    record.state = 'failed'
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=record.ks_woo_id,
                        ks_status='failed',
                        ks_type='tags',
                        ks_woo_instance_id=record.ks_instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='create',
                        response=e,
                    )
            elif record.ks_model == 'attribute':
                record.state = 'progress'
                record.env.cr.commit()
                try:
                    attribute_record = False
                    if record.ks_operation == 'odoo_to_woo':
                        attribute_record = record.env['product.attribute'].browse(record.ks_record_id)
                        attribute_record.ks_update_product_attribute_to_woo()
                    else:
                        product_attribute_data = json.loads(record.ks_data)
                        record.env['product.attribute'].ks_update_product_attribute_from_woo(
                            product_attribute_data, wcapi, record.ks_instance_id)
                    record.state = 'done'
                    if attribute_record:
                        record.ks_woo_id = attribute_record.ks_woo_id
                    self.env.cr.commit()
                except Exception as e:
                    record.state = 'failed'
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=record.ks_woo_id,
                        ks_status='failed',
                        ks_type='attribute',
                        ks_woo_instance_id=record.ks_instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='create',
                        response=e,
                    )
            elif record.ks_model == 'category':
                record.state = 'progress'
                record.env.cr.commit()
                try:
                    category_record = False
                    if record.ks_operation == 'odoo_to_woo':
                        category_record = self.env['product.category'].browse(record.ks_record_id)
                        category_record.ks_update_product_category_to_woo()
                    else:
                        product_category_data = json.loads(record.ks_data)
                        record.env['product.category'].ks_update_category_woocommerce(
                            wcapi, record.ks_instance_id, product_category_data)
                    record.state = 'done'
                    if category_record:
                        record.ks_woo_id = category_record.ks_woo_id
                    self.env.cr.commit()
                except Exception as e:
                    record.state = 'failed'
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=record.ks_woo_id,
                        ks_status='failed',
                        ks_type='category',
                        ks_woo_instance_id=record.ks_instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='create',
                        response=e,
                    )
            elif record.ks_model == 'sale_order':
                sale_order_data = json.loads(record.ks_data)
                record.state = 'progress'
                record.env.cr.commit()
                try:
                    record.env['sale.order'].ks_manage_sale_order_data(
                        sale_order_data, wcapi, record.ks_instance_id)
                    record.state = 'done'
                    self.env.cr.commit()
                except Exception as e:
                    record.state = 'failed'
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=record.ks_woo_id,
                        ks_status='failed',
                        ks_type='order',
                        ks_woo_instance_id=record.ks_instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='create',
                        response=e,
                    )
            elif record.ks_model == 'stock':
                record.state = 'progress'
                self.env.cr.commit()
                try:
                    if record.ks_operation == 'odoo_to_woo':
                        product_stock_record = self.env['product.template'].browse(record.ks_record_id)
                        product_stock_record.ks_update_product_stock(record.ks_instance_id, wcapi,
                                                                     int(record.ks_woo_id))
                        record.state = 'done'
                    else:
                        stock_data = [json.loads(record.ks_data)]
                        record.env['product.template'].ks_manage_inventory_adjustments(
                            stock_data, record.ks_instance_id, wcapi)
                        record.state = 'done'
                    self.env.cr.commit()
                except Exception as e:
                    record.state = 'failed'
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=record.ks_woo_id,
                        ks_status='failed',
                        ks_type='stock',
                        ks_woo_instance_id=record.ks_instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='create',
                        response=e,
                    )
        if self:
            self.env['ks.woo.sync.log'].create_log_param(
                ks_woo_id='',
                ks_status='success',
                ks_type='system_status',
                ks_woo_instance_id=self[0].ks_instance_id,
                ks_operation='',
                ks_operation_type='',
                response='--- Queue job has been successfully completed ---',
            )

    def ks_sync_product_tag_to_queue(self, wcapi, instance_id):
        """
        Adding batch of Tag records in the queue

        :param wcapi: API Data
        :param instance_id: Woo Instance Data
        :return: None
        """
        multi_api_call = True
        per_page = 100
        page = 1
        while (multi_api_call):
            try:
                woo_tag_response = wcapi.get("products/tags", params={"per_page": per_page, "page": page})
                if woo_tag_response.status_code in [200, 201]:
                    all_woo_tag_records = woo_tag_response.json()
                    vals = []
                    for product_tag in all_woo_tag_records:
                        ks_woo_id = product_tag.get('id')
                        product_tag_data = {
                            'ks_name': product_tag.get('name'),
                            'ks_model': 'tag',
                            'state': 'new',
                            'ks_type': 'import',
                            'ks_instance_id': instance_id.id,
                            'ks_woo_id': ks_woo_id,
                            'ks_operation': 'woo_to_odoo',
                            'ks_data': json.dumps(product_tag),
                        }
                        vals.append(product_tag_data)
                    if vals:
                        self.create(vals)
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=False,
                        ks_status='success',
                        ks_type='tags',
                        ks_woo_instance_id=instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='create',
                        response='Product Tag Record has been successfully added to queue',
                    )
                else:
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=False,
                        ks_status='failed',
                        ks_type='tags',
                        ks_woo_instance_id=instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='fetch',
                        response=str(woo_tag_response.status_code) + eval(woo_tag_response.text).get('message'),
                    )
                total_api_calls = woo_tag_response.headers._store.get('x-wp-totalpages')[1]
                remaining_api_calls = int(total_api_calls) - page
                if remaining_api_calls > 0:
                    page += 1
                else:
                    multi_api_call = False
            except ConnectionError:
                self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                    type='tags',
                                                                    operation='woo_to_odoo')

    def ks_sync_product_woocommerce_in_queue(self, wcapi, instance_id):
        """
        Adding batch of Product records in the queue

        :param wcapi: API Data
        :param instance_id: Woo Instance Data
        :return: None
                """
        multi_api_call = True
        per_page = 100
        page = 1
        ks_record_found = 0
        try:
            while (multi_api_call):
                woo_product_response = wcapi.get("products", params={"per_page": per_page, "page": page})
                if woo_product_response.status_code in [200, 201]:
                    woo_products_record = self.ks_date_filter_function(woo_product_response.json(), self._context,
                                                                       instance_id, "product")
                    vals = []
                    for product_record in woo_products_record:
                        ks_woo_product_id = product_record.get('id')
                        product_data = {
                            'ks_name': product_record.get('name'),
                            'ks_model': 'product_template',
                            'state': 'new',
                            'ks_type': 'import',
                            'ks_instance_id': instance_id.id,
                            'ks_woo_id': ks_woo_product_id,
                            'ks_operation': 'woo_to_odoo',
                            'ks_data': json.dumps(product_record),
                        }
                        vals.append(product_data)
                    if vals:
                        self.create(vals)
                    if woo_products_record:
                        ks_record_found += 1
                        self.env['ks.woo.sync.log'].create_log_param(
                            ks_woo_id=False,
                            ks_status='success',
                            ks_type='product',
                            ks_woo_instance_id=instance_id,
                            ks_operation='woo_to_odoo',
                            ks_operation_type='create',
                            response='Product Record has been successfully added to queue',
                        )
                else:
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=False,
                        ks_status='failed',
                        ks_type='product',
                        ks_woo_instance_id=instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='fetch',
                        response=str(woo_product_response.status_code) + eval(woo_product_response.text).get('message'),
                    )

                total_api_calls = woo_product_response.headers._store.get('x-wp-totalpages')[1]
                remaining_api_calls = int(total_api_calls) - page
                if remaining_api_calls > 0:
                    page += 1
                else:
                    multi_api_call = False
            if ks_record_found == 0:
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='failed',
                    ks_type='product',
                    ks_woo_instance_id=instance_id,
                    ks_operation='odoo_to_woo',
                    ks_operation_type='fetch',
                    response='No record found for that date range.',
                )
        except ConnectionError:
            self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                type='product',
                                                                operation='woo_to_odoo')
        except Exception as e:
            self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="product",
                                                         operation_type="import",
                                                         instance_id=instance_id,
                                                         operation="woo_to_odoo", exception=e)

    def ks_sync_customer_woocommerce_in_queue(self, wcapi, instance_id):
        """
        This will Sync the customer from woo to Odoo (Create and Update the customer on Odoo).

        :param wcapi: The WooCommerce API instance
        :param instance_id: The WooCommerce instance
        :return: None
        """
        multi_api_call = True
        per_page = 100
        page = 1
        ks_record_found = 0
        try:
            while (multi_api_call):
                customer_response = wcapi.get("customers", params={"per_page": per_page, "page": page})
                if customer_response.status_code in [200, 201]:
                    woo_all_customer_record = self.ks_date_filter_function(customer_response.json(), self._context,
                                                                           instance_id, "customer")
                    vals = []
                    for customer_record in woo_all_customer_record:
                        ks_woo_id = customer_record.get('id')
                        product_data = {
                            'ks_name': customer_record.get('first_name'),
                            'ks_model': 'customer',
                            'state': 'new',
                            'ks_type': 'import',
                            'ks_instance_id': instance_id.id,
                            'ks_woo_id': ks_woo_id,
                            'ks_operation': 'woo_to_odoo',
                            'ks_data': json.dumps(customer_record),
                        }
                        vals.append(product_data)
                    if vals:
                        self.create(vals)
                    if woo_all_customer_record:
                        ks_record_found += 1
                        self.env['ks.woo.sync.log'].create_log_param(
                            ks_woo_id=False,
                            ks_status='success',
                            ks_type='customer',
                            ks_woo_instance_id=instance_id,
                            ks_operation='woo_to_odoo',
                            ks_operation_type='create',
                            response='Customers Record has been successfully added to queue',
                        )
                else:
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=False,
                        ks_status='failed',
                        ks_type='customer',
                        ks_woo_instance_id=instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='fetch',
                        response=str(customer_response.status_code) + eval(customer_response.text).get('message'),
                    )
                total_api_calls = customer_response.headers._store.get('x-wp-totalpages')[1]
                remaining_api_calls = int(total_api_calls) - page
                if remaining_api_calls > 0:
                    page += 1
                else:
                    multi_api_call = False
            if ks_record_found == 0:
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='failed',
                    ks_type='customer',
                    ks_woo_instance_id=instance_id,
                    ks_operation='odoo_to_woo',
                    ks_operation_type='fetch',
                    response='No record found for that date range.',
                )
        except ConnectionError:
            self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id, type='customer',
                                                                operation='woo_to_odoo')
        except Exception as e:
            self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="customer",
                                                         operation_type="import", instance_id=instance_id,
                                                         operation="woo_to_odoo", exception=e)

    def ks_sync_product_attribute_woocommerce_to_queue(self, wcapi, instance_id):
        """
        Adding batch of Attribute records in the queue

        :param wcapi: API Data
        :param instance_id: Woo Instance Data
        :return: None
        """
        try:
            attribute_response = wcapi.get("products/attributes")
            if attribute_response.status_code in [200, 201]:
                all_woo_attributes_records = attribute_response.json()
                vals = []
                for attribute_record in all_woo_attributes_records:
                    ks_woo_id = attribute_record.get('id')
                    data = {
                        'ks_name': attribute_record.get('name'),
                        'ks_model': 'attribute',
                        'state': 'new',
                        'ks_type': 'import',
                        'ks_instance_id': instance_id.id,
                        'ks_woo_id': ks_woo_id,
                        'ks_operation': 'woo_to_odoo',
                        'ks_data': json.dumps(attribute_record),
                    }
                    vals.append(data)
                if vals:
                    self.create(vals)
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='success',
                    ks_type='attribute',
                    ks_woo_instance_id=instance_id,
                    ks_operation='woo_to_odoo',
                    ks_operation_type='create',
                    response='Attribute value has been successfully added to queue',
                )
            else:
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='failed',
                    ks_type='attribute',
                    ks_woo_instance_id=instance_id,
                    ks_operation='woo_to_odoo',
                    ks_operation_type='fetch',
                    response=str(attribute_response.status_code) + eval(attribute_response.text).get('message'),
                )
        except ConnectionError:
            self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id, type='attribute',
                                                                operation='woo_to_odoo')

    def ks_sync_coupon_from_woo_to_queue(self, wcapi, instance_id):
        """
        Adding batch of Coupon records in the queue

        :param wcapi: API Data
        :param instance_id: Woo Instance Data
        :return: None
                """
        multi_api_call = True
        per_page = 100
        page = 1
        while (multi_api_call):
            try:
                woo_coupon_response = wcapi.get("coupons", params={"per_page": per_page, "page": page})
                if woo_coupon_response.status_code in [200, 201]:
                    all_woo_coupon_records = woo_coupon_response.json()
                    vals = []
                    for coupon_record in all_woo_coupon_records:
                        ks_woo_id = coupon_record.get('id')
                        coupon = ''
                        for rec in range(0, len(coupon_record.get('code')) - 2):
                            coupon = coupon + '*'
                        for rec in range(len(coupon_record.get('code')) - 2, len(coupon_record.get('code'))):
                            coupon = coupon + coupon_record.get('code')[rec]
                        product_data = {
                            'ks_name': coupon,
                            'ks_model': 'coupon',
                            'state': 'new',
                            'ks_type': 'import',
                            'ks_instance_id': instance_id.id,
                            'ks_woo_id': ks_woo_id,
                            'ks_operation': 'woo_to_odoo',
                            'ks_data': json.dumps(coupon_record),
                        }
                        vals.append(product_data)
                    if vals:
                        self.create(vals)
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=False,
                        ks_status='success',
                        ks_type='coupon',
                        ks_woo_instance_id=instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='create',
                        response='Coupons Record has been successfully added to queue',
                    )
                else:
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=False,
                        ks_status='failed',
                        ks_type='coupon',
                        ks_woo_instance_id=instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='fetch',
                        response=str(woo_coupon_response.status_code) + eval(woo_coupon_response.text).get('message'),
                    )
                total_api_calls = woo_coupon_response.headers._store.get('x-wp-totalpages')[1]
                remaining_api_calls = int(total_api_calls) - page
                if remaining_api_calls > 0:
                    page += 1
                else:
                    multi_api_call = False
            except ConnectionError:
                self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                    type='coupon',
                                                                    operation='woo_to_odoo')

    def ks_sync_payment_gateway_in_queue(self, wcapi, instance_id):
        """
        Adding batch of Payment Gateway records in the queue

        :param wcapi: API Data
        :param instance_id: Woo Instance Data
        :return: None
        """
        if instance_id.ks_wc_version != 'wc/v1':
            try:
                p_g_response = wcapi.get("payment_gateways")
                if p_g_response.status_code in [200, 201]:
                    all_woo_payment_gateway = p_g_response.json()
                    vals = []
                    for gateway_record in all_woo_payment_gateway:
                        ks_woo_id = gateway_record.get('id')
                        product_data = {
                            'ks_name': gateway_record.get('title', ''),
                            'ks_model': 'payment_gateway',
                            'state': 'new',
                            'ks_type': 'import',
                            'ks_instance_id': instance_id.id,
                            'ks_woo_id': ks_woo_id,
                            'ks_operation': 'woo_to_odoo',
                            'ks_data': json.dumps(gateway_record),
                        }
                        vals.append(product_data)
                    if vals:
                        self.create(vals)
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=False,
                        ks_status='success',
                        ks_type='payment_gateway',
                        ks_woo_instance_id=instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='create',
                        response='Payment Gateway Record has been successfully added to queue',
                    )
                else:
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=False,
                        ks_status='failed',
                        ks_type='payment_gateway',
                        ks_woo_instance_id=instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='fetch',
                        response=str(p_g_response.status_code) + eval(p_g_response.text).get('message'),
                    )
            except ConnectionError:
                self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                    type='payment_gateway',
                                                                    operation='woo_to_odoo')
            except Exception as e:
                self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="payment_gateway",
                                                             operation_type="import", instance_id=instance_id,
                                                             operation="woo_to_odoo", exception=e)
        else:
            self.env['ks.woo.sync.log'].create_log_param(
                ks_woo_id=False,
                ks_status='failed',
                ks_type='payment_gateway',
                ks_woo_instance_id=instance_id,
                ks_operation='woo_to_odoo',
                ks_operation_type='fetch',
                response="Payment Gateway can't be synced for the Woo Instance which has version as 2.6.x or later "
                         "because for this version individual payment gateway API route is not available."
            )

    def ks_sync_product_category_to_queue(self, wcapi, instance_id):
        """
        Adding batch of Category records in the queue

        :param wcapi: API Data
        :param instance_id: Woo Instance Data
        :return: None
        """
        try:
            multi_api_call = True
            per_page = 100
            page = 1
            while (multi_api_call):
                all_woo_category_response = wcapi.get("products/categories",
                                                      params={"per_page": per_page, "page": page})
                if all_woo_category_response.status_code in [200, 201]:
                    all_woo_category_records = all_woo_category_response.json()
                    vals = []
                    for category_record in all_woo_category_records:
                        ks_woo_id = category_record.get('id')
                        product_data = {
                            'ks_name': category_record.get('name'),
                            'ks_model': 'category',
                            'state': 'new',
                            'ks_type': 'import',
                            'ks_instance_id': instance_id.id,
                            'ks_woo_id': ks_woo_id,
                            'ks_operation': 'woo_to_odoo',
                            'ks_data': json.dumps(category_record),
                        }
                        vals.append(product_data)
                    if vals:
                        self.create(vals)
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=False,
                        ks_status='success',
                        ks_type='category',
                        ks_woo_instance_id=instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='create',
                        response='Product Category Record has been successfully added to queue',
                    )
                else:
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=False,
                        ks_status='failed',
                        ks_type='category',
                        ks_woo_instance_id=instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='fetch',
                        response=str(all_woo_category_response.status_code) + eval(all_woo_category_response.text).get(
                            'message'),
                    )
                total_api_calls = all_woo_category_response.headers._store.get('x-wp-totalpages')[1]
                remaining_api_calls = int(total_api_calls) - page
                if remaining_api_calls > 0:
                    page += 1
                else:
                    multi_api_call = False
        except ConnectionError:
            self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                type='product',
                                                                operation='woo_to_odoo')
        except Exception as e:
            self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="product",
                                                         operation_type="import",
                                                         instance_id=instance_id,
                                                         operation="woo_to_odoo", exception=e)

    def ks_sync_sale_order_to_queue(self, wcapi, instance_id):
        """
        Adding batch of Sale Order records in the queue

        :param wcapi: API Data
        :param instance_id: Woo Instance Data
        :return: None
        """
        if instance_id.ks_instance_state == 'active':
            multi_api_call = True
            per_page = 100
            page = 1
            ks_record_found = 0
            try:
                sale_order_data = False
                while (multi_api_call):
                    woo_order_response = wcapi.get("orders", params={"per_page": per_page, "page": page})
                    woo_orders_record_all = self.ks_date_filter_function(woo_order_response.json(), self._context,
                                                                         instance_id, "order")
                    vals = []
                    for sale_order_record in woo_orders_record_all:
                        if sale_order_record.get('status') in instance_id.ks_import_order_state_config.filtered(
                                lambda r: r.ks_sync is True).mapped('ks_woo_states'):
                            ks_woo_id = sale_order_record.get('id')
                            sale_order_data = {
                                'ks_name': sale_order_record.get('name'),
                                'ks_model': 'sale_order',
                                'state': 'new',
                                'ks_type': 'import',
                                'ks_instance_id': instance_id.id,
                                'ks_woo_id': ks_woo_id,
                                'ks_operation': 'woo_to_odoo',
                                'ks_data': json.dumps(sale_order_record),
                            }
                            vals.append(sale_order_data)
                    if vals:
                        self.create(vals)
                        sale_order_data = True
                        ks_record_found += 1
                        self.env['ks.woo.sync.log'].create_log_param(
                            ks_woo_id=False,
                            ks_status='success',
                            ks_type='order',
                            ks_woo_instance_id=instance_id,
                            ks_operation='woo_to_odoo',
                            ks_operation_type='create',
                            response=str(len(vals)) + ' Orders has been successfully added to queue',
                        )
                    total_api_calls = woo_order_response.headers._store.get('x-wp-totalpages')[1]
                    remaining_api_calls = int(total_api_calls) - page
                    if remaining_api_calls > 0:
                        page += 1
                    else:
                        multi_api_call = False
                if not sale_order_data:
                    ks_record_found += 1
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=False,
                        ks_status='failed',
                        ks_type='order',
                        ks_woo_instance_id=instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='create',
                        response='No orders found !!',
                    )
                if ks_record_found == 0:
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=False,
                        ks_status='failed',
                        ks_type='order',
                        ks_woo_instance_id=instance_id,
                        ks_operation='odoo_to_woo',
                        ks_operation_type='fetch',
                        response='No record found for that date range.',
                    )
            except ConnectionError:
                self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                    type='order',
                                                                    operation='woo_to_odoo')
            except Exception as e:
                self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="order",
                                                             operation_type="import",
                                                             instance_id=instance_id,
                                                             operation="woo_to_odoo", exception=e)
        else:
            return self.env['ks.message.wizard'].ks_pop_up_message(names='Error', message='The instance must be in '
                                                                                          'active state to perform '
                                                                                          'the operations')

    def ks_import_stock_woocommerce_in_queue(self, wcapi, instance_id):
        """
        This will get the woocommerce product data and update the products stock quantity on odoo

        :param wcapi: The WooCommerce API instance
        :param instance_id: The WooCommerce instance
        :return: None
        """
        multi_api_call = True
        per_page = 100
        page = 1
        product_records = []
        while (multi_api_call):
            try:
                woo_product_response = wcapi.get("products", params={"per_page": per_page, "page": page})
                if woo_product_response.status_code in [200, 201]:
                    woo_products_record = woo_product_response.json()
                    vals = []
                    for product_record in woo_products_record:
                        ks_woo_id = product_record.get('id')
                        data = {
                            'ks_name': product_record.get('name'),
                            'ks_model': 'stock',
                            'state': 'new',
                            'ks_type': 'import',
                            'ks_instance_id': instance_id.id,
                            'ks_woo_id': ks_woo_id,
                            'ks_operation': 'woo_to_odoo',
                            'ks_data': json.dumps(product_record),
                        }
                        vals.append(data)
                    if vals:
                        self.create(vals)
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=False,
                        ks_status='success',
                        ks_type='stock',
                        ks_woo_instance_id=instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='create',
                        response='Product Stock value has been successfully added to queue',
                    )
                else:
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=False,
                        ks_status='failed',
                        ks_type='stock',
                        ks_woo_instance_id=instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='fetch',
                        response=str(woo_product_response.status_code) + eval(woo_product_response.text).get('message'),
                    )

                total_api_calls = woo_product_response.headers._store.get('x-wp-totalpages')[1]
                remaining_api_calls = int(total_api_calls) - page
                if remaining_api_calls > 0:
                    page += 1
                else:
                    multi_api_call = False
            except ConnectionError:
                self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                    type='stock',
                                                                    operation='woo_to_odoo',
                                                                    ks_woo_id=False)

    def ks_update_product_tag_to_queue(self, tags_records, instance_id):
        """
        This will Sync the tag from Odoo to woo

            :param tags_records: tag_records
            :return: None
        """
        if tags_records:
            vals = []
            for each_record in tags_records:
                product_tag_data = {
                    'ks_name': each_record.ks_name,
                    'ks_model': 'tag',
                    'state': 'new',
                    'ks_type': 'export',
                    'ks_instance_id': instance_id.id,
                    'ks_record_id': each_record.id,
                    'ks_woo_id': each_record.ks_woo_id,
                    'ks_operation': 'odoo_to_woo',
                }
                vals.append(product_tag_data)
            if vals:
                self.create(vals)
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='success',
                    ks_type='tags',
                    ks_woo_instance_id=instance_id,
                    ks_operation='odoo_to_woo',
                    ks_operation_type='update',
                    response='Product Tag Records has been successfully added to queue',
                )
            else:
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='failed',
                    ks_type='tags',
                    ks_woo_instance_id=instance_id,
                    ks_operation='odoo_to_woo',
                    ks_operation_type='update',
                    response='Product Tag Records have been failed to add in queue',
                )
        else:
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_type='tags',
                                                         ks_status='failed',
                                                         ks_woo_instance_id=instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='update',
                                                         response='There is no tag with ' + instance_id.display_name + ' instance.')

    def ks_update_customer_woocommerce_in_queue(self, customers_records, instance_id):
        """
        This will Sync the customer from Odoo to woo

            :param customers_records: customer records
            :return: None
        """
        if customers_records:
            vals = []
            for each_record in customers_records:
                product_customer_data = {
                    'ks_name': each_record.display_name,
                    'ks_model': 'customer',
                    'state': 'new',
                    'ks_type': 'export',
                    'ks_instance_id': instance_id.id,
                    'ks_record_id': each_record.id,
                    'ks_woo_id': each_record.ks_woo_id,
                    'ks_operation': 'odoo_to_woo',
                }
                vals.append(product_customer_data)
            if vals:
                self.create(vals)
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='success',
                    ks_type='customer',
                    ks_woo_instance_id=instance_id,
                    ks_operation='odoo_to_woo',
                    ks_operation_type='update',
                    response='Customers Records has been successfully added to queue',
                )
            else:
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='failed',
                    ks_type='customer',
                    ks_woo_instance_id=instance_id,
                    ks_operation='odoo_to_woo',
                    ks_operation_type='update',
                    response='Customers Records have been failed to add in queue',
                )
        else:
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_type='customer',
                                                         ks_status='failed',
                                                         ks_woo_instance_id=instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='update',
                                                         response='There is no customer with ' + instance_id.display_name + ' instance.')

    def ks_update_coupon_to_queue(self, coupons_records, instance_id):
        """
        This will Sync the coupon from Odoo to woo

            :param coupons_records: coupon_records
            :return: None
        """
        if coupons_records:
            vals = []
            for each_record in coupons_records:
                coupon = ''
                for rec in range(0, len(each_record.ks_coupon_code) - 2):
                    coupon = coupon + '*'
                for rec in range(len(each_record.ks_coupon_code) - 2, len(each_record.ks_coupon_code)):
                    coupon = coupon + each_record.ks_coupon_code[rec]
                product_data = {
                    'ks_name': coupon,
                    'ks_model': 'coupon',
                    'state': 'new',
                    'ks_type': 'export',
                    'ks_instance_id': instance_id.id,
                    'ks_record_id': each_record.id,
                    'ks_woo_id': each_record.ks_woo_id,
                    'ks_operation': 'odoo_to_woo',
                }
                vals.append(product_data)
            if vals:
                self.create(vals)
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='success',
                    ks_type='coupon',
                    ks_woo_instance_id=instance_id,
                    ks_operation='odoo_to_woo',
                    ks_operation_type='update',
                    response='Coupons Records has been successfully added to queue',
                )
            else:
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='failed',
                    ks_type='coupon',
                    ks_woo_instance_id=instance_id,
                    ks_operation='odoo_to_woo',
                    ks_operation_type='update',
                    response='Coupons Records have been failed to added in queue',
                )
        else:
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_type='coupon',
                                                         ks_status='failed',
                                                         ks_woo_instance_id=instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='update',
                                                         response='There is no coupon with ' + instance_id.display_name + ' instance.')

    def ks_update_product_category_to_queue(self, category_records, instance_id):
        """
        This will Sync the category from Odoo to woo

            :param category_records: category_records
            :return: None
        """
        if category_records:
            vals = []
            for each_record in category_records:
                product_category_data = {
                    'ks_name': each_record.name,
                    'ks_model': 'category',
                    'state': 'new',
                    'ks_type': 'export',
                    'ks_instance_id': instance_id.id,
                    'ks_record_id': each_record.id,
                    'ks_woo_id': each_record.ks_woo_id,
                    'ks_operation': 'odoo_to_woo',
                }
                vals.append(product_category_data)
            if vals:
                self.create(vals)
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='success',
                    ks_type='category',
                    ks_woo_instance_id=instance_id,
                    ks_operation='odoo_to_woo',
                    ks_operation_type='update',
                    response='Category Records has been successfully added to queue',
                )
            else:
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='failed',
                    ks_type='category',
                    ks_woo_instance_id=instance_id,
                    ks_operation='odoo_to_woo',
                    ks_operation_type='update',
                    response='Category Records hves been failed to add in queue',
                )
        else:
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_type='category',
                                                         ks_status='failed',
                                                         ks_woo_instance_id=instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='update',
                                                         response='There is no category with ' + instance_id.display_name + ' instance.')

    def ks_update_product_attribute_to_queue(self, attributes_records, instance_id):
        """
        This will Sync the attribute from Odoo to woo

            :param attributes_records: product_records
            :return: None
        """
        if attributes_records:
            vals = []
            for each_record in attributes_records:
                product_attribute_data = {
                    'ks_name': each_record.name,
                    'ks_model': 'attribute',
                    'state': 'new',
                    'ks_type': 'export',
                    'ks_instance_id': instance_id.id,
                    'ks_record_id': each_record.id,
                    'ks_woo_id': each_record.ks_woo_id,
                    'ks_operation': 'odoo_to_woo',
                }
                vals.append(product_attribute_data)
            if vals:
                self.create(vals)
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='success',
                    ks_type='attribute',
                    ks_woo_instance_id=instance_id,
                    ks_operation='odoo_to_woo',
                    ks_operation_type='update',
                    response='Attribute value has been successfully added to queue',
                )
            else:
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='failed',
                    ks_type='attribute',
                    ks_woo_instance_id=instance_id,
                    ks_operation='odoo_to_woo',
                    ks_operation_type='update',
                    response='Attribute value have been failed to add in queue',
                )
        else:
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_type='attribute',
                                                         ks_status='failed',
                                                         ks_woo_instance_id=instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='update',
                                                         response='There is no attribute with ' + instance_id.display_name + ' instance.')

    def ks_update_product_to_queue(self, products_records, instance_id):
        """
        This will Sync the product_records from Odoo to woo

            :param products_records: product_records
            :return: None
        """
        if products_records:
            vals = []
            for each_record in products_records:
                product_data = {
                    'ks_name': each_record.name,
                    'ks_model': 'product_template',
                    'state': 'new',
                    'ks_type': 'export',
                    'ks_instance_id': instance_id.id,
                    'ks_record_id': each_record.id,
                    'ks_woo_id': each_record.ks_woo_id,
                    'ks_operation': 'odoo_to_woo',

                }
                vals.append(product_data)
            if vals:
                self.create(vals)
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='success',
                    ks_type='product',
                    ks_woo_instance_id=instance_id,
                    ks_operation='odoo_to_woo',
                    ks_operation_type='update',
                    response='Product Records has been successfully added to queue',
                )
            else:
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='failed',
                    ks_type='product',
                    ks_woo_instance_id=instance_id,
                    ks_operation='odoo_to_woo',
                    ks_operation_type='update',
                    response='Product Records have been failed to add in queue',
                )
        else:
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_type='product',
                                                         ks_status='failed',
                                                         ks_woo_instance_id=instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='update',
                                                         response='There is no product with ' + instance_id.display_name + ' instance.')

    def ks_update_product_stock_to_queue(self, records, instance_id):
        """
        This will Sync the product stock from Odoo to woo .

            :param records: records, instance_id
            :return: None
        """
        vals = []
        for each_record in records:
            product_stock_data = {
                'ks_name': each_record.name,
                'ks_model': 'stock',
                'state': 'new',
                'ks_type': 'export',
                'ks_instance_id': instance_id.id,
                'ks_record_id': each_record.id,
                'ks_woo_id': each_record.ks_woo_id,
                'ks_operation': 'odoo_to_woo',
            }
            vals.append(product_stock_data)
        if vals:
            self.create(vals)
            self.env['ks.woo.sync.log'].create_log_param(
                ks_woo_id=False,
                ks_status='success',
                ks_type='stock',
                ks_woo_instance_id=instance_id,
                ks_operation='odoo_to_woo',
                ks_operation_type='create',
                response='Product Stock Record has been successfully added to queue',
            )
        else:
            self.env['ks.woo.sync.log'].create_log_param(
                ks_woo_id=False,
                ks_status='failed',
                ks_type='stock',
                ks_woo_instance_id=instance_id,
                ks_operation='odoo_to_woo',
                ks_operation_type='create',
                response='Product Stock Record has been failed to add in queue',
            )

    def ks_date_filter_function(self, woo_response, context, instance_id, type_of_operation):
        """
        It filter data acc to date, if no date it returns all data

        :param woo_response: Woocommerce Respone Data
        :param context: Context Data
        :param instance_id: Woo Instance Data
        :param type_of_operation: Operation Type
        :return: response
        """
        if context.get('ks_date_filter'):
            date_from = context.get('ks_date_from')
            date_to = context.get('ks_date_to')
            woo_response_filter = []
            for response in woo_response:
                if response.get('date_created'):
                    create_date = datetime.strptime(
                        (response.get('date_created') or False).replace('T', ' '),
                        DEFAULT_SERVER_DATETIME_FORMAT).date()
                    if create_date >= date_from and create_date <= date_to:
                        woo_response_filter.append(response)
            return woo_response_filter
        if not context.get('ks_date_filter'):
            return woo_response
