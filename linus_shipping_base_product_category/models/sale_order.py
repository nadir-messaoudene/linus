# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_carrier_desc = fields.Text()

    def _get_delivery_methods(self):
        _logger.info('_get_delivery_methods inherit')
        if self.partner_id.property_delivery_carrier_id:
            return self.partner_id.property_delivery_carrier_id.sudo()
        return super(SaleOrder, self)._get_delivery_methods()
