from odoo import models
from . import prepare_json_data as create_json


def _create_json_data(self, arranged_data):
    return create_json._prepare_json_data(self, self._name, arranged_data)


def _create_data_from_json(self, arranged_data, json_data):
    return create_json._prepare_odoo_data(self, self._name, arranged_data, json_data)


def _update_data_from_json(self, arranged_data, json_data):
    return create_json._update_odoo_data(self, self._name, arranged_data, json_data, self.id)


models.Model._create_json_data = _create_json_data
models.Model._create_data_from_json = _create_data_from_json
models.Model._update_data_from_json = _update_data_from_json
