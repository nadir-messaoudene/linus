# -*- coding: utf-8 -*-
# Part of Syncoria. See LICENSE file for full copyright and licensing details.

import logging
import psycopg2

from odoo import api, fields, models, registry, SUPERUSER_ID, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    categ_id = fields.Many2one('product.category', string='Product Category')
    categ_ids = fields.Many2many('product.category', 'delivery_carrier_category_rel', 'carrier_id', 'category_id', string='Product Category')

    def _get_price_available(self, order):
        self.ensure_one()
        self = self.sudo()
        order = order.sudo()
        total = weight = volume = quantity = 0
        categ_ids = self.env['product.category']
        total_delivery = 0.0
        for line in order.order_line:
            if line.state == 'cancel':
                continue
            if line.is_delivery:
                total_delivery += line.price_total
            if not line.product_id or line.is_delivery:
                continue
            if line.product_id.type == "service":
                continue
            qty = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
            weight += (line.product_id.weight or 0.0) * qty
            volume += (line.product_id.volume or 0.0) * qty
            quantity += qty
            categ_ids |= line.product_id.categ_id
        total = (order.amount_total or 0.0) - total_delivery

        total = self._compute_currency(order, total, 'pricelist_to_company')

        return self._get_price_from_order_picking(total, weight, volume, quantity, categ_ids)

    def _get_price_dict(self, total, weight, volume, quantity):
        '''Hook allowing to retrieve dict to be used in _get_price_from_picking() function.
        Hook to be overridden when we need to add some field to product and use it in variable factor from price rules. '''
        return {
            'price': total,
            'volume': volume,
            'weight': weight,
            'wv': volume * weight,
            'quantity': quantity
        }

    def _get_price_from_order_picking(self, total, weight, volume, quantity, categ_ids):
        print("_get_price_from_order_picking >>>>>>>>>>>>>>", self, total, weight, volume, quantity, categ_ids)
        price = 0.0
        criteria_found = False
        price_dict = self._get_price_dict(total, weight, volume, quantity)
        if self.free_over and total >= self.amount:
            return 0
        for categ in categ_ids:
            print("categ >>>>>>>>>>>>>>>>>>", categ)
            for line in self.price_rule_ids.filtered(lambda rule: categ in rule.categ_ids):
                print("line >>>>>>>>>>>>>", line)
                test = safe_eval(line.variable + line.operator + str(line.max_value), price_dict)
                print("test >>>>>>>>>>>>>>>>>>>>>>>", test)
                if test:
                    price = line.list_base_price + line.list_price * price_dict[line.variable_factor]
                    print("price >>>>>>>>>>>>>", price)
                    print("(1.0 + (line.margin / 100.0)) >>>>", (1.0 + (line.margin / 100.0)))
                    if line.margin:
                        price = price * (line.margin / 100.0)
                    criteria_found = True
                    break
        if not criteria_found:
            raise UserError(_("No price rule matching this order; delivery cost cannot be computed."))
        print("price >>>>>>>>>>>>>>>>>>", price)
        return price

    # def _get_price_from_picking(self, total, weight, volume, quantity):
    #     print("_get_price_from_picking >>>>>>>>>>>>>", self, total, weight, volume, quantity, self.env.context)
    #     import inspect
    #     for i in inspect.stack():
    #         print("i >>>>>>>>>>>>>>>>", i)
    #     price = 0.0
    #     criteria_found = False
    #     price_dict = self._get_price_dict(total, weight, volume, quantity)
    #     if self.free_over and total >= self.amount:
    #         return 0
    #     print("self.price_rule_ids >>>>>>>>>>>>>>", self.price_rule_ids)
    #     for line in self.price_rule_ids:
    #         test = safe_eval(line.variable + line.operator + str(line.max_value), price_dict)
    #         if test:
    #             price = line.list_base_price + line.list_price * price_dict[line.variable_factor]
    #             criteria_found = True
    #     if not criteria_found:
    #         raise UserError(_("No price rule matching this order; delivery cost cannot be computed."))

    #     return price
