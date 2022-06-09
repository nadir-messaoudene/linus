# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_delivery_methods(self):
        address = self.partner_shipping_id
        # searching on website_published will also search for available website (_search method on computed field)
        category_ids = self.order_line.mapped('product_id.categ_id.id') or False
        print("category_ids >>>>>>>>>>>>>>>>>", category_ids)
        delivery_carriers = self.env['delivery.carrier'].sudo().search([('website_published', '=', True), ('categ_ids', 'in', category_ids)])
        print("delivery_carriers >>>>>>>>>>>>>>>>>>>", delivery_carriers)
        return self.env['delivery.carrier'].sudo().search([('website_published', '=', True), ('categ_ids', 'in', category_ids)]).with_context(category_ids=category_ids).available_carriers(address)
