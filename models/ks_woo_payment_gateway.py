# -*- coding: utf-8 -*-

from odoo import models, fields, api
from requests.exceptions import ConnectionError


class KsWooPaymentGateway(models.Model):
    _name = 'ks.woo.payment.gateway'
    _description = 'WooCommerce Payment Gateway'
    _rec_name = 'ks_title'

    ks_title = fields.Char('Title')
    ks_woo_pg_id = fields.Char('Payment code', readonly=True)
    ks_description = fields.Text(string='Description')
    ks_woo_instance_id = fields.Many2one('ks.woocommerce.instances', string='Instance')
    ks_company = fields.Many2one('res.company', 'Company', related='ks_woo_instance_id.ks_company')
    ks_journal_id = fields.Many2one('account.journal', string='Payment Method', domain=[('type', 'in', ('bank', 'cash'))])

    def ks_sync_payment_gateway(self, wcapi, instance_id):
        """
        Importing the Payment Gateways to the Odoo

        :param wcapi: API Data
        :param instance_id: Woo Instance Data
        :return: None
        """
        if instance_id.ks_wc_version != 'wc/v1':
            try:
                p_g_response = wcapi.get("payment_gateways")
                if p_g_response.status_code in [200, 201]:
                    all_woo_payment_gateway = p_g_response.json()
                    for each_record in all_woo_payment_gateway:
                        exist_in_odoo = self.search([('ks_title', '=', each_record.get('title')),
                                                     ('ks_woo_pg_id', '=', each_record.get('id')),
                                                     ('ks_woo_instance_id', '=', instance_id.id)], limit=1)
                        if exist_in_odoo:
                            exist_in_odoo.write(self._ks_prepare_woo_payment_gateway_data(each_record, instance_id))
                            ks_operation_type = 'update'
                        else:
                            exist_in_odoo = self.create(self._ks_prepare_woo_payment_gateway_data(each_record, instance_id))
                            ks_operation_type = 'create'
                        self.env['ks.woo.sync.log'].create_log_param(
                            ks_woo_id=False,
                            ks_status='success',
                            ks_type='payment_gateway',
                            ks_woo_instance_id=instance_id,
                            ks_operation='woo_to_odoo',
                            ks_operation_type=ks_operation_type,
                            response='Payment Gateway [' + exist_in_odoo.ks_title + '] has been succesfully created' if ks_operation_type == 'create' else 'Payment Gateway [' + exist_in_odoo.ks_title + '] has been succesfully updated',
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

    def ks_manage_payment_gateway(self, instance_id, each_record):
        """
        Processing the Payment Gateway data to Update or Create in Odoo

        :param instance_id: Woo Instance Data
        :param each_record: Payment Gateway data
        :return: None
        """
        exist_in_odoo = self.search([('ks_title', '=', each_record.get('title')),
                                     ('ks_woo_pg_id', '=', each_record.get('id')),
                                     ('ks_woo_instance_id', '=', instance_id.id)], limit=1)
        if exist_in_odoo:
            exist_in_odoo.write(self._ks_prepare_woo_payment_gateway_data(each_record, instance_id))
            ks_operation_type = 'update'
        else:
            exist_in_odoo = self.create(self._ks_prepare_woo_payment_gateway_data(each_record, instance_id))
            ks_operation_type = 'create'
        self.env['ks.woo.sync.log'].create_log_param(
            ks_woo_id=False,
            ks_status='success',
            ks_type='payment_gateway',
            ks_woo_instance_id=instance_id,
            ks_operation='woo_to_odoo',
            ks_operation_type=ks_operation_type,
            response='Payment Gateway [' + exist_in_odoo.ks_title + '] has been succesfully created' if ks_operation_type == 'create' else 'Payment Gateway [' + exist_in_odoo.ks_title + '] has been succesfully updated',
        )

    def _ks_prepare_woo_payment_gateway_data(self, record, instance_id):
        """
        Preparing the data to be updated on the Odoo side

        :param record: Payment Gateway Data
        :param instance_id: Woo Instance Data
        :return: Data
        """
        data = {
            'ks_title': record.get('title') or '',
            'ks_woo_pg_id': record.get('id') or '',
            'ks_woo_instance_id': instance_id.id,
            'ks_description': record.get('description') or '',
        }
        return data

