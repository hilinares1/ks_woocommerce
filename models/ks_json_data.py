# -*- coding: utf-8 -*-

ADDRESS_DATA = {
    'name': 'name',
    'email': 'email',
    'phone': 'phone',
    'mobile': 'mobile',
    'comment': 'notes',
    'street': 'street',
    'street2': 'street2',
    'city': 'city',
    'state_id': 'state',
    'zip': 'zip',
    'country_id': 'country',
}

PARTNER_DATA = {
    'vat': 'vat',
    'website': 'website',
}

ATTRIBUTE_DATA = {
    'product.attribute': {
                    'name': 'name',
                    'ks_slug': 'ks_slug',
                    'type': 'type',
                    'create_variant': 'create_variant',
                    'value_ids': 'product_attribute_value',
    },
    'product.attribute.value': {
                    'id': 'id',
                    'ks_slug': 'value',
                    'name': 'value',
                    'html_color': 'html_colour',
                    'sequence': 'sequence',
                    }

}

ATTRIBUTE_VALUE_DATA = {
    'product.attribute': {
                    'id': 'id'
    },
    'product.attribute.value': {
                    'id': 'id',
                    'attribute_id': 'product_attribute',
                    'name': 'value',
                    'ks_slug': 'value',
                    'html_color': 'html_colour',
                    'sequence': 'sequence',
                    }
}
