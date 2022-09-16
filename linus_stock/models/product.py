# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

import operator as py_operator
from ast import literal_eval
from collections import defaultdict
from dateutil.relativedelta import relativedelta
from odoo import models

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import float_is_zero
from odoo.tools.float_utils import float_round


class Product(models.Model):
    _inherit = "product.product"

    def _get_domain_locations(self):
        '''
        Parses the context and returns a list of location_ids based on it.
        It will return all stock locations when no parameters are given
        Possible parameters are shop, warehouse, location, compute_child
        '''
        Warehouse = self.env['stock.warehouse']

        def _search_ids(model, values):
            ids = set()
            domain = []
            for item in values:
                if isinstance(item, int):
                    ids.add(item)
                else:
                    domain = expression.OR([[('name', 'ilike', item)], domain])
            if domain:
                ids |= set(self.env[model].search(domain).ids)
            return ids

        # We may receive a location or warehouse from the context, either by explicit
        # python code or by the use of dummy fields in the search view.
        # Normalize them into a list.
        location = self.env.context.get('location')
        if location and not isinstance(location, list):
            location = [location]
        warehouse = self.env.context.get('warehouse')
        if warehouse and not isinstance(warehouse, list):
            warehouse = [warehouse]
        # filter by location and/or warehouse
        if warehouse:
            if self.env.context.get('website_id'):
                w_ids = set(Warehouse.browse(_search_ids('stock.warehouse', warehouse)).mapped('view_location_id').ids)
                if location:
                    l_ids = _search_ids('stock.location', location)
                    location_ids = w_ids & l_ids
                else:
                    location_ids = w_ids
            else:
                location_ids = _search_ids('stock.location', warehouse)
        else:
            if location:
                location_ids = _search_ids('stock.location', location)
            else:
                location_ids = set(Warehouse.search([]).mapped('view_location_id').ids)

        return self._get_domain_locations_new(location_ids, compute_child=self.env.context.get('compute_child', True))

#
# class ProductTemplate(models.Model):
#     _inherit = 'product.template'
#
#     def _get_combination_info(self, combination=False, product_id=False, add_qty=1, pricelist=False,
#                               parent_combination=False, only_template=False):
#         combination_info = super(ProductTemplate, self)._get_combination_info(
#             combination=combination, product_id=product_id, add_qty=add_qty, pricelist=pricelist,
#             parent_combination=parent_combination, only_template=only_template)
#
#         if not self.env.context.get('website_sale_stock_get_quantity'):
#             return combination_info
#
#         if combination_info['product_id']:
#             product = self.env['product.product'].sudo().browse(combination_info['product_id'])
#             website = self.env['website'].get_current_website()
#             free_qty = product.free_qty
#             combination_info.update({
#                 'free_qty': free_qty,
#                 'product_type': product.type,
#                 'product_template': self.id,
#                 'available_threshold': self.available_threshold,
#                 'cart_qty': product.cart_qty,
#                 'uom_name': product.uom_id.name,
#                 'allow_out_of_stock_order': self.allow_out_of_stock_order,
#                 'show_availability': self.show_availability,
#                 'out_of_stock_message': self.out_of_stock_message,
#             })
#         else:
#             product_template = self.sudo()
#             combination_info.update({
#                 'free_qty': 0,
#                 'product_type': product_template.type,
#                 'allow_out_of_stock_order': product_template.allow_out_of_stock_order,
#                 'available_threshold': product_template.available_threshold,
#                 'product_template': product_template.id,
#                 'cart_qty': 0,
#             })
#
#         return combination_info
