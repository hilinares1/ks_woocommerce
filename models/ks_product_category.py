from odoo import models, fields, api
from requests import exceptions
import datetime
from requests.exceptions import ConnectionError


class KsProductCategoryInherit(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin', 'product.category']
    _name = 'product.category'

    ks_woo_id = fields.Integer('Woo Id', track_visibility='onchange',
                               readonly=True, default=0,
                               help="""Woo Id: Unique WooCommerce resource id for the product category on the specified 
                                               WooCommerce Instance""")
    ks_slug = fields.Char('Slug')
    ks_woo_description = fields.Text('Woo Description')
    ks_export_in_woo = fields.Boolean('Exported in Woo',
                                      readonly=True,
                                      store=True,
                                      compute='_ks_compute_export_in_woo',
                                      help="""Exported in Woo: If enabled, the product is synced with the specified 
                                                    WooCommerce Instance""")
    ks_woo_instance_id = fields.Many2one('ks.woocommerce.instances', track_visibility='onchange',
                                         string='Woo Instance',
                                         help="""WooCommerce Instance: Ths instance of woocomerce to which this 
                                                         category belongs to.""")
    ks_date_created = fields.Datetime('Created On', readonly=True,
                                      help="Created On: Date on which the WooCommerce Category has been created")
    ks_date_updated = fields.Datetime('Updated On', readonly=True,
                                      help="Updated On: Date on which the WooCommerce Category has been last updated")
    ks_sync_date = fields.Datetime('Modified On', readonly=True,
                                   help="Sync On: Date on which the record has been modified")
    ks_last_exported_date = fields.Datetime('Last Synced On', readonly=True)
    ks_sync_status = fields.Boolean('Sync Status', compute='sync_update', default=False)

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
        Updating the Datetime on every change in data

        :param values: Change data
        :return: None
        """
        for rec in self:
            if rec.ks_woo_id:
                values.update({'ks_sync_date': datetime.datetime.now()})
        super(KsProductCategoryInherit, self).write(values)

    @api.depends('ks_woo_id')
    def _ks_compute_export_in_woo(self):
        """
        To show the product category are exported in woo

        :return: None
        """
        for rec in self:
            rec.ks_export_in_woo = bool(rec.ks_woo_id)

    def ks_sync_product_category_woocommerce(self, wcapi, instance_id):
        """
        Sync the product category and its values from woo to Odoo

        :param wcapi: API Data
        :param instance_id: Woo Instance Data
        :return: None
        """
        try:
            multi_api_call = True
            per_page = 50
            page = 1
            while (multi_api_call):
                all_woo_category_response = wcapi.get("products/categories",
                                                      params={"per_page": per_page, "page": page})
                if all_woo_category_response.status_code in [200, 201]:
                    all_woo_category_records = all_woo_category_response.json()
                    for each_record in all_woo_category_records:
                        self.ks_update_category_woocommerce(wcapi, instance_id, each_record)
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
        except exceptions.ConnectionError:
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_status='failed',
                                                         ks_type='system_status',
                                                         ks_woo_instance_id=instance_id,
                                                         ks_operation='woo_to_odoo',
                                                         ks_operation_type='connection',
                                                         response="Couldn't Connect the Instance[ %s ] at time of Category "
                                                                  "Syncing !! Please check the network connectivity"
                                                                  " or the configuration parameters are not "
                                                                  "correctly set" % instance_id.ks_name)

    def _get_parent_categ(self, wcapi, instance_id, category_record):
        """
        Extract the parent category from the main category and updating and creating records respectively

        :param wcapi: API Data
        :param instance_id: Woo Instance Data
        :param category_record: Category Data
        :return: Category
        """
        try:
            parent_id = category_record.get('parent')
            if parent_id != 0:
                parent_categ_id = self.env['product.category'].search(
                    [('ks_woo_id', '=', parent_id), ('ks_woo_instance_id', '=', instance_id.id)], limit=1)
                if not parent_categ_id:
                    parent_response = wcapi.get("products/categories/%s" % parent_id)
                    if parent_response.status_code in [200, 201]:
                        parent_record = parent_response.json()
                        if parent_id != 0:
                            self._get_parent_categ(wcapi, instance_id, parent_record)
                        return self.create(self._prepare_woo_product_category_data(parent_record, instance_id))
                    else:
                        self.env['ks.woo.sync.log'].create_log_param(
                            ks_woo_id=parent_id,
                            ks_status='failed',
                            ks_type='category',
                            ks_woo_instance_id=instance_id,
                            ks_operation='woo_to_odoo',
                            ks_operation_type='fetch',
                            response=str(parent_response.status_code) + eval(parent_response.text).get(
                                'message') + '[Parent Category]',
                        )
                else:
                    return self.env['product.category'].search(
                        [('ks_woo_id', '=', parent_id), ('ks_woo_instance_id', '=', instance_id.id)])
        except exceptions.ConnectionError:
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_status='failed',
                                                         ks_type='system_status',
                                                         ks_woo_instance_id=instance_id,
                                                         ks_operation='woo_to_odoo',
                                                         ks_operation_type='connection',
                                                         response="Couldn't Connect the Instance[ %s ] at time of Category "
                                                                  "Syncing !! Please check the network connectivity"
                                                                  " or the configuration parameters are not "
                                                                  "correctly set" % instance_id.ks_name)

    @api.model
    def ks_update_product_category_to_odoo(self):
        """
        Sync the product category and its values from woo to Odoo

        :param wcapi: API Data
        :param instance_id: Woo Instance Data
        :return: None
        """
        ks_rec_failed_list = []
        for rec in self:
            instance_id = self.env['ks.woocommerce.instances'].browse(rec.ks_woo_instance_id.id)
            if instance_id.ks_instance_state == 'active':
                try:
                    wcapi = rec.ks_woo_instance_id.ks_api_authentication()
                    if wcapi.get("").status_code in [200, 201]:
                        all_woo_category_response = wcapi.get("products/categories/%s" % rec.ks_woo_id)
                        if all_woo_category_response.status_code in [200, 201]:
                            rec.ks_update_category_woocommerce(wcapi, instance_id, all_woo_category_response.json())
                        else:
                            self.env['ks.woo.sync.log'].create_log_param(
                                ks_woo_id=False,
                                ks_status='failed',
                                ks_type='category',
                                ks_woo_instance_id=instance_id,
                                ks_operation='woo_to_odoo',
                                ks_operation_type='fetch',
                                response=str(all_woo_category_response.status_code) + eval(
                                    all_woo_category_response.text).get('message'),
                            )
                except ConnectionError:
                    self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=instance_id,
                                                                        type='product',
                                                                        operation='woo_to_odoo')
                except Exception as e:
                    if rec.id not in ks_rec_failed_list:
                        ks_rec_failed_list.append(rec)
                    self.env['ks.woo.sync.log'].ks_exception_log(record=False, type="product",
                                                                 operation_type="import",
                                                                 instance_id=instance_id,
                                                                 operation="woo_to_odoo", exception=e)
            else:
                return 'error'
        return ks_rec_failed_list

    def ks_update_product_category_to_odoo_wizard(self):
        """
        This will import and update the product category on woocommerce.

        :return: Open a popup wizard with a summary message
        """
        ks_failed_instance_list = []
        ks_failed_product_id = []
        for rec in self:
            ks_failed_list = rec.ks_update_product_category_to_odoo()
            if ks_failed_list == 'error':
                format_info = 'The instance must be in active state or instance field should be updated to perform the operations'
                format_string = ks_message_string = ''
            else:
                for record in ks_failed_list:
                    ks_failed_product_id.append(record.display_name)
                    ks_failed_instance_list.append(record['ks_woo_instance_id'].display_name)
                format_string = ks_message_string = ''
                if len(ks_failed_product_id) != 0:
                    ks_message_string = '\n\nList of Failed Records:\n'
                    format_string = 'Name:\t' + str(ks_failed_product_id) + '\n' + 'Instance:\t' + str(
                        ks_failed_instance_list)
                format_info = 'Import Operation has been performed, Please refer logs for further details.'
            log = 'Import Status'
        return self.env['ks.message.wizard'].ks_pop_up_message(names=log,
                                                               message=format_info + ks_message_string + format_string)

    @api.model
    def ks_update_product_category_to_woo(self):
        """
        This will update the record in Odoo to Woo.

        :return: None
        """
        ks_rec_failed_list = []
        ks_list = False
        for each_record in self:
            try:
                parent_path_ids = each_record.parent_path.split('/')
                if each_record.ks_woo_instance_id and each_record.ks_woo_instance_id.ks_instance_state == 'active':
                    for parent_id in parent_path_ids:
                        if parent_id:
                            current_record = each_record.browse(int(parent_id))
                            wcapi = each_record.ks_woo_instance_id.ks_api_authentication()
                            if wcapi.get('').status_code in [200, 201]:
                                category_data = each_record._prepare_odoo_product_category_data(current_record)
                                if current_record.ks_woo_id:
                                    record_exist_status = wcapi.get("products/categories/%s" % current_record.ks_woo_id)
                                    if record_exist_status.status_code == 404:
                                        ks_list = each_record.create_category_on_woo(wcapi, current_record,
                                                                                     category_data)
                                    else:
                                        ks_list = each_record.update_category_on_woo(wcapi, current_record,
                                                                                     category_data)
                                else:
                                    ks_list = each_record.create_category_on_woo(wcapi, current_record, category_data)
                            else:
                                self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                                             ks_status='success' if wcapi.get(
                                                                                 "").status_code in [200,
                                                                                                     201] else 'failed',
                                                                             ks_type='system_status',
                                                                             ks_woo_instance_id=each_record.ks_woo_instance_id,
                                                                             ks_operation='odoo_to_woo',
                                                                             ks_operation_type='connection',
                                                                             response='Connection successful' if wcapi.get(
                                                                                 "").status_code in [200,
                                                                                                     201] else wcapi.get(
                                                                                 "").text)
                else:
                    self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=each_record.ks_woo_id,
                                                                 ks_status='failed',
                                                                 ks_type='category',
                                                                 ks_woo_instance_id=each_record.ks_woo_instance_id,
                                                                 ks_operation='odoo_to_woo',
                                                                 ks_operation_type='update' if each_record.ks_woo_id else 'create',
                                                                 response='WooCommerce instance was not selected' if not each_record.ks_woo_instance_id else
                                                                 "WooCommerce instance is not in active state to perform this operation")
                    return 'error'
            except ConnectionError:
                self.env['ks.woo.sync.log'].ks_connection_error_log(instance_id=each_record.ks_woo_instance_id,
                                                                    type='category',
                                                                    operation='odoo_to_woo')
            except Exception as e:
                if each_record.id not in ks_rec_failed_list:
                    ks_rec_failed_list.append(each_record)
                self.env['ks.woo.sync.log'].ks_exception_log(record=each_record, type="category",
                                                             operation_type="create" if each_record.ks_woo_id else "update",
                                                             instance_id=each_record.ks_woo_instance_id,
                                                             operation="odoo_to_woo", exception=e)
        return ks_rec_failed_list if len(ks_rec_failed_list) > 0 else (ks_list if type(ks_list) is list else [])

    def ks_update_product_category_to_woo_wizard(self):
        """
        This will export and update the product category on woocommerce.

        :return: Open a popup wizard with a summary message
        """
        ks_failed_instance_list = []
        ks_failed_product_id = []
        for rec in self:
            ks_failed_list = rec.ks_update_product_category_to_woo()
            if ks_failed_list == 'error':
                format_info = 'The instance must be in active state or instance field should be updated to perform the operations'
                format_string = ks_message_string = ''
            else:
                for record in ks_failed_list:
                    ks_failed_product_id.append(record.name)
                    ks_failed_instance_list.append(record['ks_woo_instance_id'].display_name)
                format_string = ks_message_string = ''
                if len(ks_failed_product_id) != 0:
                    ks_message_string = '\n\nList of Failed Records:\n'
                    format_string = 'Name:\t' + str(ks_failed_product_id) + '\n' + 'Instance:\t' + str(
                        ks_failed_instance_list)
                format_info = 'Export Operation has been performed, Please refer logs for further details.'
            log = 'Export Status'
        return self.env['ks.message.wizard'].ks_pop_up_message(names=log,
                                                               message=format_info + ks_message_string + format_string)

    def update_category_on_woo(self, wcapi, current_record, category_data):
        """
        Update the category on the Woocommerce side

        :param wcapi: API Data
        :param current_record: Category Data
        :param category_data: Category JSON Data
        :return: Failed record list
        """
        ks_rec_failed_list = []
        try:
            woo_categ_response = wcapi.put("products/categories/%s" % current_record.ks_woo_id, category_data)
            if woo_categ_response.status_code in [200, 201]:
                status = 'success'
            else:
                status = 'failed'
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=current_record.ks_woo_id,
                                                         ks_status=status,
                                                         ks_type='category',
                                                         ks_woo_instance_id=current_record.ks_woo_instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='update',
                                                         response='Category [' + current_record.name + '] has been succesfully updated' if status == 'success' else 'The update operation failed for Category [' + current_record.name + '] due to ' + eval(
                                                             woo_categ_response.text).get('message'))
            if status == 'success':
                current_record.ks_sync_date = datetime.datetime.now()
                current_record.ks_last_exported_date = current_record.ks_sync_date
                current_record.sync_update()
            else:
                if current_record.id not in ks_rec_failed_list:
                    ks_rec_failed_list.append(current_record)
        except exceptions.ConnectionError:
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=current_record.ks_woo_id,
                                                         ks_status='failed',
                                                         ks_type='system_status',
                                                         ks_woo_instance_id=current_record.ks_woo_instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='connection',
                                                         response="Couldn't Connect the Instance[ %s ] at time of Attribute "
                                                                  "Updation !! Please check the network connectivity"
                                                                  " or the configuration parameters are not "
                                                                  "correctly set" % current_record.ks_woo_instance_id.ks_name)
        except Exception as e:
            if current_record.id not in ks_rec_failed_list:
                ks_rec_failed_list.append(current_record)
            self.env['ks.woo.sync.log'].ks_exception_log(record=current_record, type="customer",
                                                         operation_type="update",
                                                         instance_id=current_record.ks_woo_instance_id,
                                                         operation="odoo_to_woo", exception=e)
        return ks_rec_failed_list

    def create_category_on_woo(self, wcapi, current_record, category_data):
        """
        Will create Category in WooCommerce.

        :param current_record: Odoo product.category record
        :param category_data: Category json data
        :return: THe category record
        """
        ks_rec_failed_list = []
        try:
            woo_category_response = wcapi.post("products/categories", category_data)
            ks_woo_id = False
            if woo_category_response.status_code in [200, 201]:
                woo_category_data = woo_category_response.json()
                current_record.ks_woo_id = ks_woo_id = woo_category_data.get('id')
                current_record.ks_slug = woo_category_data.get('slug')
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=ks_woo_id,
                                                         ks_status='success' if woo_category_response.status_code in [
                                                             200,
                                                             201] else 'failed',
                                                         ks_type='category',
                                                         ks_woo_instance_id=current_record.ks_woo_instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='create',
                                                         response='Category [' + current_record.name + '] has been succesfully exported ' if woo_category_response.status_code in [
                                                             200,
                                                             201] else 'The export operation failed for Category [' + current_record.name + '] due to ' + eval(
                                                             woo_category_response.text).get('message'))
            if woo_category_response.status_code in [200, 201]:
                current_record.ks_sync_date = datetime.datetime.now()
                current_record.ks_last_exported_date = current_record.ks_sync_date
                current_record.sync_update()
            else:
                if current_record.id not in ks_rec_failed_list:
                    ks_rec_failed_list.append(current_record)
            return ks_rec_failed_list if len(ks_rec_failed_list) > 0 else current_record

        except exceptions.ConnectionError:
            self.env['ks.woo.sync.log'].create_log_param(ks_woo_id=False,
                                                         ks_status='failed',
                                                         ks_type='system_status',
                                                         ks_woo_instance_id=current_record.ks_woo_instance_id,
                                                         ks_operation='odoo_to_woo',
                                                         ks_operation_type='connection',
                                                         response="Couldn't Connect the Instance[ %s ] at time of Category "
                                                                  "Updation !! Please check the network connectivity"
                                                                  " or the configuration parameters are not "
                                                                  "correctly set" % current_record.ks_woo_instance_id.ks_name)
        except Exception as e:
            if current_record.id not in ks_rec_failed_list:
                ks_rec_failed_list.append(current_record)
            self.env['ks.woo.sync.log'].ks_exception_log(record=current_record, type="customer",
                                                         operation_type="create",
                                                         instance_id=current_record.ks_woo_instance_id,
                                                         operation="odoo_to_woo", exception=e)
        return ks_rec_failed_list

    def ks_update_category_woocommerce(self, wcapi, instance_id, category_record):
        """
        Create or Update Category to Odoo side

        :param wcapi: API Data
        :param instance_id: Woo Instance Data
        :param category_record: Category Data
        :return: Catgory Data after creation or updation
        """
        category_exist_in_odoo = self.search([('ks_woo_id', '=', category_record.get('id')),
                                              ('ks_woo_instance_id', '=', instance_id.id)], limit=1)
        woo_formated_data = self._prepare_woo_product_category_data(category_record, instance_id)
        if category_record.get('parent') != 0:
            category = self._get_parent_categ(wcapi, instance_id, category_record)
            woo_formated_data.update({'parent_id': category.id})
        else:
            woo_formated_data.update({'parent_id': []})
        if category_exist_in_odoo:
            category_exist_in_odoo.write(woo_formated_data)
            ks_operation_type = 'update'
        else:
            category_exist_in_odoo = self.create(woo_formated_data)
            ks_operation_type = 'create'
        self.env['ks.woo.sync.log'].create_log_param(
            ks_woo_id=category_exist_in_odoo.ks_woo_id,
            ks_status='success',
            ks_type='category',
            ks_woo_instance_id=instance_id,
            ks_operation='woo_to_odoo',
            ks_operation_type=ks_operation_type,
            response='Category [' + category_exist_in_odoo.name + '] has been succesfully created' if ks_operation_type == 'create' else 'Category [' + category_exist_in_odoo.name + '] has been succesfully updated',
        )
        category_exist_in_odoo.ks_sync_date = datetime.datetime.now()
        category_exist_in_odoo.ks_last_exported_date = category_exist_in_odoo.ks_sync_date
        category_exist_in_odoo.sync_update()
        return category_exist_in_odoo

    def update_category_on_odoo(self, json_data, instance_id, wcapi):
        """
        Sync the product category and its values from woo to Odoo for a product

        :param instance_id: Category data in product
        :param wcapi: The WooCommerce API instance
        :param instance_id: The WooCommerce instance
        :return: None
        """
        if json_data:
            odoo_categ_ids = []
            for each_record in json_data:
                all_woo_category_response = wcapi.get("products/categories/%s" % each_record.get('id'))
                if all_woo_category_response.status_code in [200, 201]:
                    odoo_categ_ids.append(
                        self.ks_update_category_woocommerce(wcapi, instance_id, all_woo_category_response.json()).id)
                else:
                    self.env['ks.woo.sync.log'].create_log_param(
                        ks_woo_id=False,
                        ks_status='failed',
                        ks_type='category',
                        ks_woo_instance_id=instance_id,
                        ks_operation='woo_to_odoo',
                        ks_operation_type='fetch',
                        response=str(all_woo_category_response.status_code) + eval(
                            all_woo_category_response.text).get('message'),
                    )
            return odoo_categ_ids

    def _prepare_woo_product_category_data(self, json_data, instance_id):
        """
        Preparing Data for Odoo End

        :param json_data: Woocommerce Data
        :param instance_id: Woo Instance Data
        :return: Data
        """
        data = {
            "name": json_data.get('name'),
            "ks_slug": json_data.get('slug') or '',
            "ks_woo_id": json_data.get('id'),
            "ks_woo_instance_id": instance_id.id,
            "ks_woo_description": json_data.get("description") or ''
        }
        if json_data.get('parent'):
            data.update({"parent_id": self.search([('ks_woo_id', '=', json_data.get('parent')),
                                                   ('ks_woo_instance_id', '=', instance_id.id)], limit=1).id})
        return data

    def _prepare_odoo_product_category_data(self, each_record):
        """
        Preparing Data for the Woocommerce End

        :param each_record: Category Data
        :return: Data
        """
        data = {
            "name": each_record.name if each_record.name else '',
            "slug": each_record.ks_slug if each_record.ks_slug else '',
            "parent": each_record.parent_id.ks_woo_id if each_record.parent_id.ks_woo_id else 0,
            "description": each_record.ks_woo_description if each_record.ks_woo_description else ''
        }
        return data
