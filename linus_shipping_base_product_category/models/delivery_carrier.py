# -*- coding: utf-8 -*-
# Part of Syncoria. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    is_category_base_shipment = fields.Boolean(default=False)

    def _get_price_available(self, order):
        self.ensure_one()
        self = self.sudo()
        order = order.sudo()
        total = weight = volume = quantity = 0
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
        total = (order.amount_total or 0.0) - total_delivery

        total = self._compute_currency(order, total, 'pricelist_to_company')

        if self.is_category_base_shipment:
            categ_ids = list(set([line.product_id.categ_id for line in order.order_line if not line.is_delivery]))
            categ_qty_list = []
            for categ_id in categ_ids:
                product_qty = 0
                price_subtotal = 0
                for line in order.order_line:
                    if line.product_id.categ_id.id == categ_id.id and not line.is_delivery:
                        product_qty += line.product_uom_qty
                        price_subtotal += line.price_subtotal
                categ_qty_list.append(
                    {'categ_id': categ_id, 'product_qty': product_qty, 'price_subtotal': price_subtotal})
            return self._get_price_order_from_picking(total, weight, volume, quantity, categ_qty_list, order)
        return self._get_price_from_picking(total, weight, volume, quantity)

    def _get_price_order_from_picking(self, total, weight, volume, quantity, categ_qty_list, order):

        if self.free_over and total >= self.amount:
            return 0
        vp_price, vp_so_description_list = self._get_price_order_from_picking_price(total, weight, volume, quantity,
                                                                                    categ_qty_list, order)
        print('vp_price, vp_so_description_list', vp_price, vp_so_description_list)

        vq_price, vq_so_description_list = self._get_price_order_from_picking_qty(total, weight, volume, quantity,
                                                                                  categ_qty_list, order)
        print('vq_price, vq_so_description_list', vq_price, vq_so_description_list)
        price = vp_price + vq_price
        so_description_list = vp_so_description_list + vq_so_description_list
        so_description_text = ''
        for so_description in so_description_list:
            so_description_text += so_description + ', '
        order.write({'delivery_carrier_desc': so_description_text})
        return price

    def _get_price_order_from_picking_price(self, total, weight, volume, quantity, categ_qty_list, order):
        price = 0.0
        so_description_list = []
        criteria_found = False
        for line in self.price_rule_ids:
            if line.variable_factor == 'price':
                categ_ids = [line.categ_id.id for line in line.categ_price_ids if
                             line.rule_id.variable_factor == 'price']
                current_price = sum(
                    [categ_qty['price_subtotal'] for categ_qty in categ_qty_list if
                     categ_qty['categ_id'].id in categ_ids])
                total = current_price
                price_dict = self._get_price_dict(total, weight, volume, quantity)
                test = safe_eval(line.formula, price_dict)
                if test:
                    rulewise_price = 0.0
                    for categ_price_id in line.categ_price_ids:
                        current_categ_price = sum([categ_qty['price_subtotal'] for categ_qty in categ_qty_list if
                                                   categ_qty['categ_id'].id == categ_price_id.categ_id.id])
                        total += current_categ_price
                    price_dict = self._get_price_dict(total, weight, volume, quantity)
                    price += line.list_base_price + categ_price_id.list_price + line.list_price * price_dict[
                        line.variable_factor]
                    rulewise_price += line.list_base_price + categ_price_id.list_price + line.list_price * price_dict[
                        line.variable_factor]
                    criteria_found = True
                    so_description_list.append(
                        ((line.description or '') + ': ' + str(rulewise_price and order.currency_id.symbol or '') + (
                                (rulewise_price) and str(rulewise_price) or 'Free')))
        if not criteria_found:
            raise UserError(_("No price rule matching this order; delivery cost cannot be computed."))
        return price, so_description_list

    def _get_price_order_from_picking_qty(self, total, weight, volume, quantity, categ_qty_list, order):
        price = 0.0
        so_description_list = []
        criteria_found = False
        for line in self.price_rule_ids:
            if line.variable_factor == 'quantity':
                categ_ids = [line.categ_id.id for line in line.categ_price_ids if
                             line.rule_id.variable_factor == 'quantity']
                current_qty = sum(
                    [categ_qty['product_qty'] for categ_qty in categ_qty_list if categ_qty['categ_id'].id in categ_ids])
                quantity = current_qty
                price_dict = self._get_price_dict(total, weight, volume, quantity)
                test = safe_eval(line.formula, price_dict)
                if test:
                    rulewise_price = 0.0
                    for categ_price_id in line.categ_price_ids:
                        current_categ_qty = sum([categ_qty['product_qty'] for categ_qty in categ_qty_list if
                                                 categ_qty['categ_id'].id == categ_price_id.categ_id.id])
                        quantity = current_categ_qty

                        price_dict = self._get_price_dict(total, weight, volume, quantity)
                        price += line.list_base_price + (line.list_price + categ_price_id.list_price) * price_dict[
                            line.variable_factor]
                        rulewise_price += line.list_base_price + (line.list_price + categ_price_id.list_price) * \
                                          price_dict[
                                              line.variable_factor]
                    criteria_found = True
                    so_description_list.append(
                        ((line.description or '') + ': ' + str(rulewise_price and order.currency_id.symbol or '') + (
                                (rulewise_price) and str(rulewise_price) or 'Free')))
        if not criteria_found:
            raise UserError(_("No price rule matching this order; delivery cost cannot be computed."))
        return price, so_description_list
