# -*- coding: utf-8 -*-

from odoo import models, fields, api
import datetime


class KsWooSyncLog(models.Model):
    _name = 'ks.woo.sync.log'
    _description = 'WooCommerce Sync Logs'
    _rec_name = 'ks_type'
    _order = 'ks_date desc'

    ks_type = fields.Selection([('order', 'Orders'), ('product', 'Product'), ('product_variant', 'Product Variant'),
                                ('stock', 'Stock'), ('price', 'Price'), ('category', 'Category'), ('tags', 'Tags'),
                                ('customer', 'Customer'), ('payment_gateway', 'Payment Gateway'), ('coupon', 'Coupon'),
                                ('attribute', 'Attribute'), ('attribute_value', 'Attribute Values'),
                                ('system_status', 'System Status'), ('refund', 'Refund')],
                               string="Type")
    ks_woo_instance_id = fields.Many2one('ks.woocommerce.instances', 'Woo Instance')
    ks_woo_id = fields.Integer('WooCommerce Record Id', readonly=True, default=0)
    ks_date = fields.Datetime('Date')
    ks_company = fields.Many2one('res.company', 'Company', related='ks_woo_instance_id.ks_company')
    ks_operation = fields.Selection([('woo_to_odoo', 'Woo to Odoo'), ('odoo_to_woo', 'Odoo to Woo')],
                                    string="Operation")
    ks_operation_type = fields.Selection([('create', 'Create'), ('fetch', 'Fetch'), ('batch_update', 'Update'),
                                          ('update', 'Update'), ('connection', 'Connection'), ('refund', 'Refund')], string="Operation Type")
    ks_status = fields.Selection([('success', 'Success'), ('failed', 'Failed')], string="Operation Status")
    ks_message = fields.Text('Summary')

    def create_log_param(self, ks_status, ks_woo_id, ks_type, ks_woo_instance_id, ks_operation, ks_operation_type,
                         response):
        """
        :param ks_operation: The kind of operation
        :param ks_operation_type: The json data to be mapped
        :return: Dictionary of data to be used for log generation
        :rtype: Dict
        """
        params = {
            'ks_status': ks_status,
            'ks_type': ks_type,
            'ks_woo_id': ks_woo_id,
            'ks_woo_instance_id': ks_woo_instance_id.id,
            'ks_date': fields.datetime.now(),
            'ks_operation': ks_operation,
            'ks_operation_type': ks_operation_type,
            'ks_message': response
        }
        self.sudo().create(params)

    def ks_connection_error_log(self, instance_id, type, operation, ks_woo_id=False):
        """
        Generates the log related to the Connection Established

        :param instance_id: Woo Instance Data
        :param type: Operation Type
        :param operation: Odoo to Woo OR Woo to Odoo
        :param ks_woo_id: Woo Id
        :return: None
        """
        self.create_log_param(ks_woo_id=ks_woo_id,
                              ks_status='failed',
                              ks_type=type,
                              ks_woo_instance_id=instance_id,
                              ks_operation=operation,
                              ks_operation_type='connection',
                              response="Couldn't Connect the Instance[ %s ] at time of Customer "
                                       "Syncing !! Please check the network connectivity"
                                       " or the configuration parameters are not "
                                       "correctly set" % instance_id.ks_name)

    def ks_exception_log(self, record, type, operation_type, instance_id, operation, exception):
        """
        Creating the Log related to the Exception Raised

        :param record: Current Record Data
        :param type: Type
        :param operation_type: Operation Type Data
        :param instance_id: Woo Instance Data
        :param operation: Odoo to Woo OR Woo to Odoo
        :param exception: Exception Data
        :return: None
        """
        record_type = type.upper()
        o_type = ' ' + operation_type + ' ' if operation_type else ' '
        response = record_type + o_type + 'failed due to %s' % exception
        self.create_log_param(ks_woo_id=record.ks_woo_id if record else False,
                              ks_status='failed',
                              ks_type=type,
                              ks_operation_type=False,
                              ks_woo_instance_id=instance_id,
                              ks_operation=operation,
                              response=response)

    def ks_no_instance_log(self, record, type):
        """
        Generating log based on No Instance Selected

        :param record: Current Record Data
        :param type: Operation Type
        :return: None
        """
        self.create_log_param(ks_woo_id=record.ks_woo_id,
                              ks_status='failed',
                              ks_type=type,
                              ks_woo_instance_id=record.ks_woo_instance_id,
                              ks_operation='odoo_to_woo',
                              ks_operation_type='update' if record.ks_woo_id else 'create',
                              response='WooCommerce instance was not selected' if not record.ks_woo_instance_id else
                              "WooCommerce instance is not in active state to perform this operation")
