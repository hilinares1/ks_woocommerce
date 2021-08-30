# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime


class KsAccountTaxInherit(models.Model):
    _inherit = 'account.tax'

    ks_woo_id = fields.Integer('Woo Id',
                               readonly=True, default=0,
                               help="""Woo Id: Unique WooCommerce resource id for the tax on the specified 
                                       WooCommerce Instance""")
    ks_woo_instance_id = fields.Many2one('ks.woocommerce.instances',
                                         string='Woo Instance',
                                         help="""WooCommerce Instance: Ths instance of woocomerce to which this 
                                                 tax belongs to.""")
    ks_export_in_wo = fields.Boolean('Exported in Woo',
                                     readonly=True,
                                     store=True,
                                     compute='_ks_compute_export_in_woo',
                                     help="""Exported in Woo: If enabled, the Woo Tax is synced with the specified 
                                        WooCommerce Instance""")

    @api.depends('ks_woo_id')
    def _ks_compute_export_in_woo(self):
        """
        This will make enable the Exported in Woo if record has the WooCommerce Id

        :return: None
        """
        for rec in self:
            rec.ks_export_in_wo = bool(rec.ks_woo_id)


class KsAccountPaymentInherit(models.Model):
    _inherit = 'account.payment'

    ks_woo_payment_id = fields.Many2one('ks.woo.payment.gateway', 'Woo Payment Gateway',
                                        help="""Woo Payment Gateway: The WooCommerce payment gateway through which the 
                                        payment has been completed for the Woo Orders"""
                                        )
    ks_woo_sale_order_id = fields.Many2one('sale.order', string='Woo Order',
                                           help="""Woo Order: The WooCommerce Order""", readonly=1)

    @api.model
    def default_get(self, fields):
        """
        This will add the woo payment gateway and sale order for manual payment into the account payment
        """
        rec = super(KsAccountPaymentInherit, self).default_get(fields)
        invoice_defaults = self.resolve_2many_commands('invoice_ids', rec.get('invoice_ids'))
        if invoice_defaults and len(invoice_defaults) == 1:
            invoice = invoice_defaults[0]
            if invoice['ks_woo_order_id']:
                ks_woo_sale_order_id = invoice['ks_woo_order_id'][0]
                woo_order = self.env['sale.order'].browse(ks_woo_sale_order_id)
                if woo_order:
                    rec['ks_woo_sale_order_id'] = woo_order.id
                    rec['ks_woo_payment_id'] = woo_order.ks_woo_payment_gateway.id
        return rec

    @api.onchange("ks_woo_payment_id")
    def _ks_assign_woo_payment_journal(self):
        """
        This will change the journal id according to payment gateway of Woo
        """
        if self.ks_woo_payment_id:
            if self.ks_woo_payment_id.ks_journal_id:
                self.journal_id = self.ks_woo_payment_id.ks_journal_id
            else:
                if self.ks_woo_sale_order_id:
                    if self.ks_woo_sale_order_id.ks_woo_instance_id.ks_journal_id:
                        self.journal_id = self.ks_woo_sale_order_id.ks_woo_instance_id.ks_journal_id


class KsAccountInvoiceInherit(models.Model):
    _inherit = 'account.invoice'

    ks_woo_order_id = fields.Many2one('sale.order', string='Woo Order', help="""Woo Order: The WooCommerce Order""",
                                      readonly=1)


class KsAccountMoveInherit(models.Model):
    _inherit = 'account.move'

    ks_woo_order_id = fields.Many2one('sale.order', string='Woo Order', help="""Woo Order: The WooCommerce Order""",
                                      readonly=1)
    ks_refund_done = fields.Boolean('Refund Button Visibility', invisible=True, default=False)

    def ks_prepare_data_to_refund(self):
        """
        Prepare Data for the refund process on Woocommerce Side

        :return: Prepared data
        """
        time = datetime.today().strftime('%H:%M:%S')
        date = datetime.today().strftime('%Y-%m-%d')
        date_created = date + 'T' + time
        reason_index = self.ref.find(',')
        reason = self.ref[reason_index+1:] if reason_index !=-1 else " "
        data = {
            'date_created': date_created,
            'amount': str(self.amount_total),
            'reason': reason,
            'refunded_by': self.user_id.id,
            'api_refund': False
        }
        return data

    def refund_in_woo(self):
        """
        Initiating the refund process in Woocommerce through API

        :return: None
        """
        ks_instance_id = self.env['ks.woocommerce.instances'].browse(self.ks_woo_order_id.ks_woo_instance_id.id)
        wcapi = ks_instance_id.ks_api_authentication()
        order_id = self.ks_woo_order_id.ks_woo_id
        prepared_data_for_woo = self.ks_prepare_data_to_refund()
        if ks_instance_id.ks_instance_state == 'active':
            try:
                response = wcapi.post("orders/%s/refunds" % order_id, prepared_data_for_woo)
                if response.status_code in [200, 201]:
                    self.env['ks.message.wizard'].ks_pop_up_message(names='Refund Info',
                                                                    message="Refund has been Successfully Initated.\nPlease Refer Logs for more details")
                    self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=str(order_id),
                                                                 ks_status='success',
                                                                 ks_type='refund',
                                                                 ks_woo_instance_id=ks_instance_id,
                                                                 ks_operation='odoo_to_woo',
                                                                 ks_operation_type='update',
                                                                 response='Refund successful')
                    self.ks_refund_done = True
                    self.type = 'entry'
                    self.ks_woo_order_id.ks_woo_status = 'refunded'
                else:
                    self.env['ks.message.wizard'].ks_pop_up_message(names='Refund Info',
                                                                    message="Fatal Error! Refund Operation Failed.\nKindly Refer Logs for more details")
                    self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=str(order_id),
                                                                 ks_status='failed',
                                                                 ks_type='refund',
                                                                 ks_woo_instance_id=ks_instance_id,
                                                                 ks_operation='odoo_to_woo',
                                                                 ks_operation_type='update',
                                                                 response='Refund Failed' if not response.text.split('message":')[1].split(",") else response.text.split('message":')[1].split(",")[0])
            except ConnectionError:
                self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=ks_instance_id,
                                                                    type='refund',
                                                                    operation='odoo_to_woo')
            except Exception as e:
                self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="refund",
                                                             operation_type="export",
                                                             instance_id=ks_instance_id,
                                                             operation="odoo_to_woo", exception=e)
        else:
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_status='failed',
                                                         ks_type='refund',
                                                         ks_woo_instance_id=ks_instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='create',
                                                         response='Refund Order Action: Did not Found the WooCommerce Instance' if not ks_instance_id else
                                                         "Refund Order Action: WooCommerce instance is not in active state to perform this operation")


# class KsStockPickingInherit(models.Model):
#     _inherit = 'stock.picking'
#
#     def button_validate(self):
#         """
#         Updating the Sale Order Status
#
#         :return: Super call calue
#         """
#         res = super(KsStockPickingInherit, self).button_validate()
#         ks_instance_id = self.env['ks.woocommerce.instances'].browse(self.sale_id.ks_woo_instance_id.id)
#         if ks_instance_id.ks_woo_auto_order_status:
#             self.env['sale.order'].browse(self.sale_id.id).ks_woo_status = ks_instance_id.ks_woo_order_shipment_selection
#         return res
