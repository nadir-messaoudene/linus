# -*- coding: utf-8 -*-
# Part of Syncoria. See LICENSE file for full copyright and licensing details.

import logging
import psycopg2

from odoo import api, fields, models, registry, SUPERUSER_ID, _

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    categ_id = fields.Many2one('product.category', string='Product Category')
    categ_ids = fields.Many2many('product.category', 'delivery_carrier_category_rel', 'carrier_id', 'category_id', string='Product Category')
