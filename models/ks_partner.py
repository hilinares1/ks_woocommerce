# -*- coding: utf-8 -*-

from odoo import models, fields, api
from requests.exceptions import ConnectionError
import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class KsPartnerInherit(models.Model):
    _inherit = 'res.partner'

    ks_woo_id = fields.Integer('WooCommerce Id', default=0,
                               readonly=True,
                               help="""Woo Id: Unique WooCommerce resource id for the customer on the specified 
                                           WooCommerce Instance""")
    ks_woo_instance_id = fields.Many2one('ks.woocommerce.instances',
                                         string='Woo Instance',
                                         help="""WooCommerce Instance: Ths instance of woocomerce to which this 
                                                     customer belongs to.""")
    ks_export_in_wo = fields.Boolean(string='Exported in Woo',
                                     readonly=True,
                                     store=True,
                                     compute='_ks_compute_export_in_woo',
                                     help="""Exported in Woo: If enabled, the customer is synced with the specified 
                                            WooCommerce Instance""")
    ks_date_created = fields.Datetime(string='Created On',
                                      readonly=True,
                                      help="Created On: Date on which the WooCommerce Customer has been created")
    ks_date_updated = fields.Datetime(string='Updated On',
                                      readonly=True,
                                      help="Updated On: Date on which the WooCommerce customer has been last updated")
    ks_woo_username = fields.Char(string='Woo Username[Must be unique]')
    ks_sync_date = fields.Datetime(string='Modified On', readonly=True,
                                   help="Sync On: Date on which the record has been modified")
    ks_last_exported_date = fields.Datetime(string='Last Synced On', readonly=True)
    ks_sync_status = fields.Boolean(string='Sync Status', compute='sync_update', default=False)

    def sync_update(self):
        """
        Update the Date and Time on every sync to Odoo or Woocommerce

        :return: None
        """
        for rec in self:
            if rec.ks_last_exported_date and rec.ks_sync_date:
                ks_reduced_ks_sync_time = rec.ks_last_exported_date - datetime.timedelta(seconds=30)
                ks_increased_ks_sync_time = rec.ks_last_exported_date + datetime.timedelta(seconds=30)
                if rec.ks_sync_date > ks_reduced_ks_sync_time and rec.ks_sync_date < ks_increased_ks_sync_time:
                    rec.ks_sync_status = True
                else:
                    rec.ks_sync_status = False
            else:
                rec.ks_sync_status = False

    def write(self, values):
        """
        Update the date and time of every change in the record

        :param values: The Updated Data
        :return: None
        """
        for rec in self:
            if rec.ks_woo_id:
                values.update({'ks_sync_date': datetime.datetime.now()})
        super(KsPartnerInherit, self).write(values)

    def name_get(self):
        """
        Customer Name string

        :return: Super call
        """
        if self and not len(self) > 1:
            for rec in self:
                if rec.parent_id.name == "Guest Customer":
                    return [(rec.id, rec.name+'\n'+rec.contact_address.replace('\n\n', '\n'))]
                else:
                    return super(KsPartnerInherit, self).name_get()
        else:
            return super(KsPartnerInherit, self).name_get()

    @api.depends('ks_woo_id')
    def _ks_compute_export_in_woo(self):
        """
        This will make enable the Exported in Woo if record has the WooCommerce Id

        :return: None
        """
        for rec in self:
            rec.ks_export_in_wo = bool(rec.ks_woo_id)

    @api.model
    def ks_update_customer_to_odoo(self):
        """
        This will Sync the customer from woo to Odoo (Create and Update the customer on Odoo).

        :param wcapi: The WooCommerce API instance
        :param instance_id: The WooCommerce instance
        :return: None
        """
        ks_rec_failed_list = []
        for rec in self:
            instance_id = self.env['ks.woocommerce.instances'].browse(rec.ks_woo_instance_id.id)
            if instance_id.ks_instance_state == 'active':
                try:
                    wcapi = rec.ks_woo_instance_id.ks_api_authentication()
                    if wcapi.get("").status_code in [200, 201]:
                        customer_response = wcapi.get("customers/%s" % rec.ks_woo_id)
                        if customer_response.status_code in [200, 201]:
                            rec.ks_manage_customer_woo_data(instance_id, customer_response.json())
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
                except ConnectionError:
                    self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id, type='customer',
                                                                        operation='woo_to_odoo')
                except Exception as e:
                    if rec.id not in ks_rec_failed_list:
                        ks_rec_failed_list.append(rec)
                    self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="customer",
                                                                 operation_type="import", instance_id=instance_id,
                                                                 operation="woo_to_odoo", exception=e)
            else:
                return 'error'
        return ks_rec_failed_list

    def ks_import_individual_customer_to_odoo_wizard(self):
        """
        Open Log wizard after the completion on the individual record import

        :return: Wizard popup
        """
        ks_failed_instance_list = []
        ks_failed_product_id = []
        for rec in self:
            ks_failed_list = rec.ks_update_customer_to_odoo()
            if ks_failed_list == 'error':
                format_info = 'The instance must be in active state or instance field should be updated to perform ' \
                              'the operations '
                format_string = ks_message_string = ''
                log = 'Import Status'
            else:
                for record in ks_failed_list:
                    ks_failed_product_id.append(record.name)
                    ks_failed_instance_list.append(record['ks_woo_instance_id'].display_name)
                log = 'Import Status'
                format_string = ks_message_string = ''
                if len(ks_failed_product_id) != 0:
                    ks_message_string = '\n\nList of Failed Records:\n'
                    format_string = 'Name:\t' + str(ks_failed_product_id) + '\n' + 'Instance:\t' + str(
                        ks_failed_instance_list)
                format_info = 'Import Operation has been performed, Please refer logs for further details.'
        return self.env['ks.message.wizard'].ks_pop_up_message(names=log,
                                                               message=format_info + ks_message_string + format_string)

    def ks_sync_customer_woocommerce(self, wcapi, instance_id):
        """
        This will Sync the customer from woo to Odoo (Create and Update the customer on Odoo).

        :param wcapi: The WooCommerce API instance
        :param instance_id: The WooCommerce instance
        :return: None
        """
        multi_api_call = True
        per_page = 100
        page = 1
        while (multi_api_call):
            try:
                customer_response = wcapi.get("customers", params={"per_page": per_page, "page": page})
                if customer_response.status_code in [200, 201]:
                    all_woo_customer_record = customer_response.json()
                    for each_record in all_woo_customer_record:
                        self.ks_manage_customer_woo_data(instance_id, each_record)
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
            except ConnectionError:
                self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id, type='customer', operation='woo_to_odoo')
            except Exception as e:
                self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="customer",
                                                             operation_type="import", instance_id=instance_id,
                                                             operation="woo_to_odoo", exception=e)

    def ks_manage_customer_woo_data(self, instance_id, json_data):
        """
        Managing the customer data on the odoo

        :param instance_id: Current instance
        :param json_data: Woocommerce data
        :return: None
        """
        exist_in_odoo = self.search([('ks_woo_id', '=', json_data.get('id')),
                                     ('ks_woo_instance_id', '=', instance_id.id)], limit=1)
        if exist_in_odoo:
            exist_in_odoo._update_partner_details(self._ks_prepare_woo_customer_data(json_data))
            ks_operation_type = 'update'
        else:
            exist_in_odoo = self.create(self._prepare_create_data(self._ks_prepare_woo_customer_data(json_data)))
            ks_operation_type = 'create'
        exist_in_odoo.ks_woo_instance_id = instance_id.id
        exist_in_odoo.ks_woo_username = json_data.get('username') or ''
        exist_in_odoo.ks_date_created = datetime.datetime.strptime((json_data.get('date_created')).replace('T', ' '),
                                                          DEFAULT_SERVER_DATETIME_FORMAT) if json_data.get('date_created') else False
        exist_in_odoo.ks_date_updated = datetime.datetime.strptime((json_data.get('date_modified')).replace('T', ' '),
                                                          DEFAULT_SERVER_DATETIME_FORMAT) if json_data.get('date_modified') else False
        self.env['ks.woocommerce.instances'].ks_store_record_after_export(exist_in_odoo, json_data)
        self.env['ks.woo.sync.log'].create_log_param(
            ks_woo_id=exist_in_odoo.ks_woo_id,
            ks_status='success',
            ks_type='customer',
            ks_woo_instance_id=instance_id,
            ks_operation='woo_to_odoo',
            ks_operation_type=ks_operation_type,
            response='Customer [' + exist_in_odoo.name + '] has been succesfully created' if ks_operation_type == 'create' else 'Customer [' + exist_in_odoo.name + '] has been succesfully updated')
        exist_in_odoo.ks_sync_date = datetime.datetime.now()
        exist_in_odoo.ks_last_exported_date = exist_in_odoo.ks_sync_date
        exist_in_odoo.sync_update()

    def ks_update_customer_to_woo(self):
        """
        This will Export and Update the new customer from odoo to Woo

        :return: Open a popup wizard with a summary message
        """
        ks_rec_failed_list = []
        ks_list = False
        for record in self:
            data = record._ks_prepare_customer_data(record.create_json_data())
            if record.ks_woo_instance_id and record.ks_woo_instance_id.ks_instance_state == 'active':
                try:
                    wcapi = record.ks_woo_instance_id.ks_api_authentication()
                    if wcapi.get('').status_code in [200, 201]:
                        if record.ks_woo_id:
                            woo_customer_response = wcapi.get("customers/%s" % record.ks_woo_id)
                            # Check if customer exist in Woo also
                            if woo_customer_response.status_code == 404:
                                ks_list = self.ks_create_customer_on_woo(wcapi, data, record)
                            else:
                                ks_list = self.ks_update_customer_on_woo(wcapi, data, record)
                        else:
                            ks_list = self.ks_create_customer_on_woo(wcapi, data, record)
                    else:
                        self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                                     ks_status='success' if wcapi.get(
                                                                         "").status_code in [
                                                                                                200,
                                                                                                201] else 'failed',
                                                                     ks_type='system_status',
                                                                     ks_woo_instance_id=record.ks_woo_instance_id,
                                                                     ks_operation='odoo_to_woo',
                                                                     ks_operation_type='connection',
                                                                     response='Connection successful' if wcapi.get("").status_code in [200, 201] else wcapi.get("").text)
                        if wcapi.get("").status_code in [200, 201]:
                            record.ks_sync_date = datetime.datetime.now()
                            record.ks_last_exported_date = record.ks_sync_date
                            record.sync_update()
                        else:
                            if record.id not in ks_rec_failed_list:
                                ks_rec_failed_list.append(record)
                except ConnectionError:
                    self.env['ks.woo.sync.log'].ks_connection_error_log(record.ks_woo_instance_id, type='customer',
                                                                        operation='odoo_to_woo')
                except Exception as e:
                    if record.id not in ks_rec_failed_list:
                        ks_rec_failed_list.append(record)
                    self.env['ks.woo.sync.log'].ks_exception_log(record=record, type="customer",
                                                                 operation_type="export", instance_id=record.ks_woo_instance_id,
                                                                 operation="odoo_to_woo", exception=e)
            else:
                self.env['ks.woo.sync.log'].ks_no_instance_log(record, type='customer')
                return 'error'
        return ks_rec_failed_list if len(ks_rec_failed_list) > 0 else (ks_list if type(ks_list) is list else [])

    def ks_update_customer_to_woo_wizard(self):
        """
        Open Log wizard after the completion on the individual record export

        :return: Wizard popup
        """
        ks_failed_instance_list = []
        ks_failed_product_id = []
        for rec in self:
            # rec.ks_update_customer_to_woo()
            ks_failed_list = rec.ks_update_customer_to_woo()
            if ks_failed_list == 'error':
                format_info = 'The instance must be in active state or instance field should be updated to perform the operations'
                format_string = ks_message_string = ''
                log = 'Export Status'
            else:
                for record in ks_failed_list:
                    ks_failed_product_id.append(record.name)
                    ks_failed_instance_list.append(record['ks_woo_instance_id'].display_name)
                log = 'Export Status'
                format_string = ks_message_string = ''
                if len(ks_failed_product_id) != 0:
                    ks_message_string = '\n\nList of Failed Records:\n'
                    format_string = 'Name:\t' + str(ks_failed_product_id) + '\n' + 'Instance:\t' + str(
                        ks_failed_instance_list)
                format_info = 'Export Operation has been performed, Please refer logs for further details.'
            return self.env['ks.message.wizard'].ks_pop_up_message(names=log,
                                                                   message=format_info + ks_message_string + format_string)

    def ks_create_customer_on_woo(self, wcapi, data, record):
        """
        This will Create customer on Woo

        :param wcapi: The WooCommerce API instance
        :param data: The json data to be created on Woo
        :param record: The odoo customer record to be created on woo
        :return: Dictionary of Created Woo customer
        :rtype: dict
        """
        ks_rec_failed_list = []
        try:
            woo_customer_response = wcapi.post("customers", data)
            woo_customer_record = {}
            ks_woo_id = False
            if woo_customer_response.status_code in [200, 201]:
                woo_customer_record = woo_customer_response.json()
                ks_woo_id = woo_customer_record.get('id')
                record.ks_woo_username = woo_customer_record.get('username') or ''
                self.env['ks.woocommerce.instances'].ks_store_record_after_export(record, woo_customer_record)
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=ks_woo_id,
                                                         ks_status='success' if woo_customer_response.status_code in [
                                                             200,
                                                             201] else 'failed',
                                                         ks_type='customer',
                                                         ks_woo_instance_id=record.ks_woo_instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='create',
                                                         response='Customer [' + record.name + '] has been succesfully exported ' if woo_customer_response.status_code in [
                                                             200,
                                                             201] else 'The export operation failed for Customer [' + record.name + '] due to ' + eval(
                                                             woo_customer_response.text).get('message'))
            if woo_customer_response.status_code in [200, 201]:
                record.ks_sync_date = datetime.datetime.now()
                record.ks_last_exported_date = record.ks_sync_date
                record.sync_update()
            else:
                if record.id not in ks_rec_failed_list:
                    ks_rec_failed_list.append(record)
            return ks_rec_failed_list if len(ks_rec_failed_list) > 0 else woo_customer_record

        except ConnectionError:
            self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=record.ks_woo_instance_id,
                                                                type='customer',
                                                                operation='odoo_to_woo')
        except Exception as e:
            if record.id not in ks_rec_failed_list:
                ks_rec_failed_list.append(record)
            self.env['ks.woo.sync.log'].ks_exception_log(record=record, type="customer",
                                                         operation_type="create", instance_id=record.ks_woo_instance_id,
                                                         operation="odoo_to_woo", exception=e)
        return ks_rec_failed_list

    def ks_update_customer_on_woo(self, wcapi, data, record):
        """
        Update customer on Woo

        :param wcapi: The WooCommerce API instance
        :param data: The json data to be updated on Woo
        :param record: The odoo customer record to be updated on woo
        :return: None
        """
        ks_rec_failed_list = []
        try:
            woo_customer_response = wcapi.put("customers/%s" % record.ks_woo_id, data)
            if woo_customer_response.status_code in [200, 201]:
                woo_customer_record = woo_customer_response.json()
                record.ks_woo_username = woo_customer_record.get('username') or ''
                self.env['ks.woocommerce.instances'].ks_store_record_after_export(record, woo_customer_record)
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=record.ks_woo_id,
                                                         ks_status='success' if woo_customer_response.status_code in [
                                                             200,
                                                             201] else 'failed',
                                                         ks_type='customer',
                                                         ks_woo_instance_id=record.ks_woo_instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='update',
                                                         response='Customer [' + record.name + '] has been succesfully updated ' if woo_customer_response.status_code in [
                                                             200,
                                                             201] else 'The update operation failed for Customer [' + record.name + '] due to ' + eval(
                                                             woo_customer_response.text).get('message'))
            if woo_customer_response.status_code in [200, 201]:
                record.ks_sync_date = datetime.datetime.now()
                record.ks_last_exported_date = record.ks_sync_date
                record.sync_update()
            else:
                if record.id not in ks_rec_failed_list:
                    ks_rec_failed_list.append(record)
        except ConnectionError:
            self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=record.ks_woo_instance_id,
                                                                type='customer',
                                                                operation='odoo_to_woo',
                                                                ks_woo_id=record.ks_woo_id)
        except Exception as e:
            if record.id not in ks_rec_failed_list:
                ks_rec_failed_list.append(record)
            self.env['ks.woo.sync.log'].ks_exception_log(record=record, type="customer",
                                                         operation_type="update", instance_id=record.ks_woo_instance_id,
                                                         operation="odoo_to_woo", exception=e)
        return ks_rec_failed_list

    def _ks_prepare_customer_data(self, json_data):
        """
        This will Prepare Customer Data for Odoo to Woo

        :param json_data: The json data to be mapped
        :return: Dictionary of mapped data for odoo to woo
        :rtype: Dict
        """
        data = {
            "email": json_data.get('address').get('email') if json_data.get('address') else '',
            "first_name": json_data.get('address').get('name') if json_data.get('address') else '',
            "last_name": "",
        }
        if self.ks_woo_username:
            data.update({
                "username": self.ks_woo_username
            })
        else:
            data.update({
                "username": json_data.get('address').get('name') if json_data.get('address') else ''
            })
        if json_data.get('invoice_address'):
            address_data = json_data.get('invoice_address')
            data["billing"] = {
                "first_name": address_data.get('name') or '',
                "last_name": '',
                "company": self.env.user.company_id.name,
                "address_1": address_data.get('street') or '',
                "address_2": address_data.get('street2') or '',
                "city": address_data.get('city') or '',
                "state": self.env['res.country.state'].browse(address_data.get('state')).code
                if address_data.get('state') else '',
                "postcode": address_data.get('zip') or '',
                "country": self.env['res.country'].browse(address_data.get('country')).code
                if address_data.get('state') else '',
                "email": address_data.get('email') or '',
                "phone": address_data.get('phone') or ''
            }
        if json_data.get('delivery_address'):
            address_data = json_data.get('delivery_address')
            data["shipping"] = {
                "first_name": address_data.get('name') or '',
                "last_name": '',
                "company": self.env.user.company_id.name,
                "address_1": address_data.get('street') or '',
                "address_2": address_data.get('street2') or '',
                "city": address_data.get('city') or '',
                "state": self.env['res.country.state'].browse(address_data.get('state')).code
                if address_data.get('state') else '',
                "postcode": address_data.get('zip') or '',
                "country": self.env['res.country'].browse(address_data.get('country')).code
                if address_data.get('state') else ''
            }
        return data

    def _ks_prepare_woo_customer_data(self, json_data):
        """
        This will Prepare Woo Customer Data for woo to Odoo

        :param json_data: The json data to be mapped
        :return: Dictionary of mapped data for woo to odoo
        :rtype: Dict
        """
        data = {"vat": "",
                "website": ""}
        if json_data.get('shipping'):
            shipping_data = json_data.get('shipping')
            data["delivery_address"] = {
                "name": "%s %s" % (shipping_data.get('first_name'), shipping_data.get('last_name') or '') or '',
                "street": shipping_data.get('address_1') or '',
                "street2": shipping_data.get('address_2') or '',
                "city": shipping_data.get('city') or '',
                "state": shipping_data.get('state') or False,
                "zip": shipping_data.get('postcode') or '',
                "country": shipping_data.get('country') or False
            }
        if json_data.get('billing'):
            billing_data = json_data.get('billing')
            data["invoice_address"] = {
                "name": "%s %s" % (billing_data.get('first_name'), billing_data.get('last_name') or '') or '',
                "street": billing_data.get('address_1') or '',
                "street2": billing_data.get('address_2') or '',
                "city": billing_data.get('city') or '',
                "state": billing_data.get('state') or False,
                "zip": billing_data.get('postcode') or '',
                "country": billing_data.get('country') or False,
                "email": billing_data.get('email') or '',
                "phone": billing_data.get('phone') or ''
            }
        if json_data.get('first_name') or json_data.get('last_name') or json_data.get('username'):
            data["address"] = {
                    "name": "%s %s" % (json_data.get('first_name'), json_data.get('last_name') or '') if json_data.get('first_name') or json_data.get('last_name') else json_data.get('username'),
                    "street": data["invoice_address"].get('street') or '',
                    "street2": data["invoice_address"].get('street2') or '',
                    "city": data["invoice_address"].get('city') or '',
                    "state": data["invoice_address"].get('state') or False,
                    "zip": data["invoice_address"].get('zip') or '',
                    "country": data["invoice_address"].get('country') or False,
                    "email": json_data.get('email') or '',
                    "phone": data["invoice_address"].get('phone') or ''
                }
        return data
