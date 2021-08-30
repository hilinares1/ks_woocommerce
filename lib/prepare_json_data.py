import logging

model_tables = {}
RELATIONAL_DOMAINS = {
                'product.template': {
                    'connector_id': 'connector_id'
                },
                'product.attribute': {
                    'name': 'name',
                },
                'product.category': {
                    'connector_id': 'category_id'
                },
                'product.attribute.value': {
                    'name': 'value',
                    'attribute_id.name': 'attribute_name'
                },
                'product.template.attribute.line': {
                    'attribute_id.name': 'attribute_name'
                },
                'res.partner': {
                    'id': 'id',
                    'name': 'name'
                },
                'product.product': {
                    'connector_id': 'connector_id',
                    'variant_name': 'variant_name'
                },
                'res.currency': {
                    'id': 'id',
                    'name': 'name'
                },
                'uom.uom': {
                        'name': 'name'
                },
                'stock.warehouse': {
                    'id': 'id'
                },
                'account.tax': {
                    'id': 'id'
                },
                'res.country.state': {
                    'id': 'id'
                },
                'res.country': {
                    'id': 'id'
                },
                'product.pricelist': {
                    'id': 'id'
                },
                'sale.order.line': {
                    'connector_id': 'connector_id'
                }
}


def _prepare_json_data(self, model, data_dict):
    _update_global_data(data_dict)
    json_datas = []
    for model_id in self:
        json_datas.append(_prepare_fields_data(model_id, model))
    return json_datas


def _prepare_odoo_data(self, model, data_dict, json_data):
    _update_global_data(data_dict)
    return _prepare_create_data(self, json_data, model)


def _prepare_fields_data(self, model):
    model_data = self.read()[0]
    model_fields = self._fields
    json_data = {}
    if model_tables.get(model):
        for key, value in model_tables.get(model).items():
            json_data[value] = _get_relational_field_data(self, model_data.get(key), key, model_fields) or ''
    else:
        logging.info("model not getting for %s" % (model))
    return json_data


def _get_relational_field_data(self, data_id, key, fields):
    if fields.get(key):
        if fields.get(key).type == 'many2one':
            return _prepare_fields_data(self.env[fields.get(key).comodel_name].browse(data_id[0]),
                                        fields.get(key).comodel_name) if data_id else {}
        elif fields.get(key).type in ['one2many', 'many2many']:
            json_data = []
            for data_id in data_id:
                json_data.append(_prepare_fields_data(self.env[fields.get(key).comodel_name].browse(data_id)[0],
                                 fields.get(key).comodel_name)
                                 )
            return json_data
        elif fields.get(key).type in ['datetime', 'date']:
            return str(data_id)
        return data_id
    else:
        logging.info("field not getting for key " % key)


def _update_odoo_data(self, model, data_dict, json_data):
    _update_global_data(data_dict)
    data = _prepare_create_data(self, json_data, model)
    return data


def _prepare_create_data(self, json_data, model):
    create_data = {}
    try:
        for key, value in model_tables.get(model).items():
            if json_data.get(value):
                create_data[key] = _create_fields_data(self, json_data.get(value), key, model)
    except Exception as e:
        logging.info(model)
        logging.info(e)
    return create_data


def _create_fields_data(self, json_data, field, model):
    all_fields = self.env[model]._fields
    if all_fields.get(field).type == 'many2one':
        check_existing = _check_existing_value(self, json_data, all_fields.get(field).comodel_name)
        if check_existing:
            return check_existing
        return self.env[all_fields.get(field).comodel_name].create(
            _prepare_create_data(self, json_data, all_fields.get(field).comodel_name)).id
    elif all_fields.get(field).type == 'one2many':
        one2_many_list = _get_one2many_data(self, json_data, field, all_fields.get(field).comodel_name)
        return one2_many_list
    elif all_fields.get(field).type == 'many2many':
        many2many_list = []
        for data in json_data:
            existing_id = _check_existing_value(self, data, all_fields.get(field).comodel_name)
            if not existing_id:
                existing_id = self.env[all_fields.get(field).comodel_name].create(
                    _prepare_create_data(self, data, all_fields.get(field).comodel_name)).id
            many2many_list.append(existing_id)
        return [(6, 0, many2many_list)]
    return json_data


def _get_one2many_data(self, datas, field, comodel_name):
    field_data = []
    for data in datas:
        existing_id = _check_existing_value(self, data, comodel_name)
        if existing_id:
            field_data.append((1, existing_id, _prepare_create_data(self, data, comodel_name)))
        else:
            field_data.append((0, 0, _prepare_create_data(self, data, comodel_name)))
    return field_data


def _check_existing_value(self, json_data, model):
    domain = _get_domain(self, json_data, model)
    return self.env[model].search(domain, limit=1).id


def _get_domain(self, json_data, model):
    domain = []
    try:
        for key, value in RELATIONAL_DOMAINS.get(model).items():
            key_value = json_data.get(value)
            for key_dict in key.split('.')[1:]:
                key_value = key_value.get(key_dict)
            domain.append((key, '=', key_value))
    except Exception as e:
        logging.info(e)
        logging.info(model)
        return []
    return domain


def _update_global_data(data_dict):
    global model_tables
    model_tables = data_dict
