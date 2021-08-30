# -*- coding: utf-8 -*-

from odoo import fields, models, api


class KsUpdateStockAtOnce(models.TransientModel):
    _name = 'ks.update.stock.at.once'
    _description = 'This is used to Sync all the stock'
    _rec_name = 'ks_name'

    ks_name = fields.Char()
    product_ids = fields.Many2many('product.template', string="Products")
    start_date = fields.Datetime()
    end_date = fields.Datetime()
    ks_instance_id = fields.Many2one('ks.woocommerce.instances', string='Instance', readonly=True)

    @api.onchange('start_date')
    def _onchange_start_date(self):
        """
        Changing End Date based on the Start Date

        :return: None
        """
        if self.start_date and self.end_date and self.end_date < self.start_date:
            self.end_date = self.start_date

    @api.onchange('end_date')
    def _onchange_end_date(self):
        """
        Changing Start Date based on the End Date

        :return: None
        """
        if self.end_date and self.end_date < self.start_date:
            self.start_date = self.end_date

    def ks_update_stock_at_once(self):
        """
        Update Inventory Adjustment

        :return: Sucess Wizard Popups
        """
        instance = self.ks_instance_id
        if not self.product_ids:
            draft_stock_inventory = self.env['stock.inventory'].search(
                [('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date),
                 ('state', 'in', ['draft'])])
        if self.product_ids:
            draft_stock_inventory_list = self.env['stock.inventory'].search(
                [('create_date', '>=', self.start_date), ('create_date', '<=', self.end_date),
                 ('state', 'in', ['draft'])])
            draft_stock_inventory = self.get_stock_inventory(draft_stock_inventory_list, self.product_ids)
        draft_stock_inventory_list = list(draft_stock_inventory)
        draft_stock_inventory_instance = []
        for stock in draft_stock_inventory_list:
            for products in stock.line_ids:
                if products.product_id.ks_woo_instance_id.id == self.ks_instance_id.id:
                    if stock not in draft_stock_inventory_instance:
                        draft_stock_inventory_instance.append(stock)
        if len(draft_stock_inventory_instance) == 0:
            return self.env['ks.message.wizard'].ks_pop_up_message(names='Success',
                                                                   message="There is no record in draft stage for that date range")

        for stock in draft_stock_inventory_instance:
            try:
                stock.action_start()
                stock.action_validate()
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='success',
                    ks_type='stock',
                    ks_woo_instance_id=instance,
                    ks_operation='woo_to_odoo',
                    ks_operation_type='update',
                    response='Inventory adjustment ' + stock.display_name + ' has been validated.'
                )
            except Exception as e:
                self.env['ks.woo.sync.log'].create_log_param(
                    ks_woo_id=False,
                    ks_status='failed',
                    ks_type='stock',
                    ks_woo_instance_id=instance,
                    ks_operation='woo_to_odoo',
                    ks_operation_type='update',
                    response=e
                )
        return self.env['ks.message.wizard'].ks_pop_up_message(names='Success',
                                                               message="Please refer logs for further details")

    def get_stock_inventory(self, draft_stock_inventory_list, product_template):
        """
        Get Stock for Product Variant

        :param draft_stock_inventory_list: Stock Inventory in Draft State
        :param product_template: Product Data
        :return: Draft Stock Inventory
        """
        draft_stock_inventory = []
        product_ids = product_template.mapped('product_variant_ids')
        for inventory in draft_stock_inventory_list:
            for line_id in inventory.line_ids:
                if line_id.product_id in product_ids and inventory not in draft_stock_inventory:
                    draft_stock_inventory.append(inventory)
        return draft_stock_inventory
