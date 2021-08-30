# -*- coding: utf-8 -*-

from odoo import models, fields
from . import ks_json_data

ADDRESS_DATA = ks_json_data.ADDRESS_DATA
PARTNER_DATA = ks_json_data.PARTNER_DATA


class PartnerConnectorSyncing(models.Model):
    _inherit = 'res.partner'

    def create_json_data(self):
        """
        Preparing the data for the export to Woocommerce

        :return: Json Data
        """
        for rec in self:
            addresses = rec.address_get(['delivery', 'invoice'])
            partner = rec.read()[0]
            json_data = {
                'language': rec._get_language_from_code(rec.lang) or '',
                'invoice_address': rec._get_json_address_format(addresses.get('invoice')),
                'delivery_address': rec._get_json_address_format(addresses.get('delivery')),
                'address': rec._get_json_address_format(rec.id)
            }
            json_data.update({
                value: partner.get(key) or "" for key, value in PARTNER_DATA.items()
            })
            return json_data

    def _get_json_address_format(self, partner_id):
        """
        Preparing the format of Address data

        :param partner_id: Contact data
        :return: Address Data
        """
        partner = self.search_read([('id', '=', partner_id)])[0]
        return {
            value: partner.get(key)[0]
            if isinstance(partner.get(key), tuple) and len(partner.get(key)) == 2 else partner.get(key)
            for key, value in ADDRESS_DATA.items() if partner.get(key)
        }

    def _prepare_partner_data(self, json_data):
        """
        Preparing the Partner data to import in odoo

        :param json_data: Woocommerce Data
        :return: Contact Data
        """
        partner_data = {key: json_data.get(PARTNER_DATA.get(key)) for key in PARTNER_DATA if json_data.get(key)}
        partner_data.update({
            'customer': True,
        })

        if json_data.get('language'):
            partner_data.update({
                    'lang': self._get_language_code(json_data.get('language')) or False,
                })
        if json_data.get('address'):
            partner_address = self._make_address_data(json_data.get('address'))
            if partner_address:
                partner_data.update(partner_address)
        return partner_data

    def _prepare_create_data(self, json_data):
        """
        Preparing the Address data and updating in odoo side

        :param json_data: Woocommerce Data
        :return: Contact Data
        """
        partner_data = self._prepare_partner_data(json_data)
        other_addresses = self._add_address(json_data)
        if other_addresses:
            partner_data.update({'child_ids': other_addresses})
        return partner_data

    def _update_partner_details(self, json_data):
        """
        Updating the Contact data to the odoo

        :param json_data: Woocommerce Data
        :return: Address Data
        """
        address_id = False
        partner_data = self._prepare_partner_data(json_data)
        for i in ['invoice_address', 'delivery_address']:
            if json_data.get(i):
                main_add_data = json_data.get('address') or {"name": self.name if self.name else '',
                                                             "street": self.street if self.street else '',
                                                             "street2": self.street2 if self.street2 else '',
                                                             "city": self.city if self.city else '',
                                                             "state": self.state_id.code if self.state_id.code else False,
                                                             "zip": self.zip if self.zip else '',
                                                             "country": self.country_id.code if self.country_id.code else False,
                                                             "email": self.email if self.email else '',
                                                             "phone": self.phone if self.phone else ''
                                                             }
                address_data = self._match_address(main_add_data, json_data.get(i))
                if not address_data:
                    addresses = self.child_ids.filtered(lambda x: x.type == i.split('_')[0])
                    new_address = False
                    for each_add in addresses:
                        if not new_address:
                            address = {
                                "name": each_add.name if each_add.name else '',
                                "street": each_add.street if each_add.street else '',
                                "street2": each_add.street2 if each_add.street2 else '',
                                "city": each_add.city if each_add.city else '',
                                "state": each_add.state_id.code if each_add.state_id.code else False,
                                "zip": each_add.zip if each_add.zip else '',
                                "country": each_add.country_id.code if each_add.country_id.code else False,
                                "email": each_add.email if each_add.email else '',
                                "phone": each_add.phone if each_add.phone else ''
                            }
                            new_address = self._match_address(address, json_data.get(i))
                            if new_address:
                                address_id = each_add.id
                    updated_address = self._make_address_data(json_data.get(i))
                    if not new_address:
                        if updated_address:
                            updated_address['type'] = i.split('_')[0]
                            updated_address['parent_id'] = self.id
                            address_id = self.env['res.partner'].create(updated_address).id
        self.write(partner_data)
        return address_id

    # make invoice and delivery address
    def _add_address(self, json_data):
        """
        Adding the main address and the child address in odoo

        :param json_data: Woocommerce Data
        :return: Child Address
        """
        child_addresses = []
        for i in ['invoice_address', 'delivery_address']:
            if json_data.get('address') and json_data.get(i):
                address_data = self._match_address(json_data.get('address'), json_data.get(i))
                if not address_data:
                    address_data = self._make_address_data(json_data.get(i))
                    if address_data:
                        address_data['type'] = i.split('_')[0]
                        child_addresses.append((0, 0, address_data))
        return child_addresses

    def _make_address_data(self, address):
        """
        Creating the address with country and state

        :param address: Address Data
        :return: Address
        """
        data = {}
        for key, value in ADDRESS_DATA.items():
            if self._fields.get(key).type != 'many2one':
                if address.get(value):
                    data[key] = address.get(value)
            else:
                if key == 'country_id':
                    country_id = self.env[self._fields.get(key).comodel_name].search([
                                    ('code', '=', address.get(value))], limit=1)
                    if not country_id and address.get(value):
                        country_id = self.env[self._fields.get(key).comodel_name].create(
                            {'code': address.get(value), 'name': address.get(value)})
                    if address.get(value):
                        data[key] = country_id.id
                if key == 'state_id':
                    country_id = self.env['res.country'].search([
                                    ('code', '=', address.get('country'))], limit=1)
                    if not country_id and address.get('country'):
                        country_id = self.env['res.country'].create(
                            {'code': address.get('country'), 'name': address.get('country')})
                    state_id = self.env[self._fields.get(key).comodel_name].search([
                        ('code', '=', address.get(value)), ('country_id', '=', country_id.id)], limit=1)
                    if not state_id and address.get('state') and country_id:
                        state_id = self.env[self._fields.get(key).comodel_name].create(
                            {'code': address.get(value), 'name': address.get(value), 'country_id': country_id.id})
                    if state_id:
                        data[key] = state_id.id
        if len(data) == 1 and len(data.get('name')) == 1 and not data.get('name').strip():
            data.pop('name')
        return data

    def _match_address(self, address1, address2):
        """
        Matching the Address with the existing address on odoo side if it exist or not

        :param address1: Main Address
        :param address2: Secondary Address
        :return: Boolean Value
        """
        if address1 and address2:
            if {c: address1[c] for c in address1 if c in address2 and address1[c] != address2[c]}:
                for key, value in {c: address1[c] for c in address1 if
                                   c in address2 and address1[c] != address2[c]}.items():
                    if value:
                        return False
        return True

    def _get_language_code(self, json_language):
        """
        Extract the Language code

        :param json_language: Woocommerce Language data
        :return: Language or False
        """
        language = [language for language in self.env['res.lang'].get_installed()
                    if language[1].upper() == json_language.upper()]
        return language[0][0] if language else False

    def _get_language_from_code(self, code):
        """
        Extracgting the Language from the language code

        :param code: Language code
        :return: Language
        """
        language = [i[1] for i in self.env['res.lang'].get_installed() if i[0] == code]
        if language:
            return language[0]
