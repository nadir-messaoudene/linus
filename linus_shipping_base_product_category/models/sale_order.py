# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_carrier_desc = fields.Text()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_categ_id = fields.Many2one('product.category', string='Product Category',
                                       compute='_compute_product_categ_id', store=True)

    @api.depends('product_id')
    def _compute_product_categ_id(self):
        for line in self:
            if line.product_id:
                line.product_categ_id = line.product_id.categ_id.id
