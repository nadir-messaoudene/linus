# -*- coding: utf-8 -*-
# Part of Syncoria. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    is_category = fields.Boolean(default=False)

    def _get_price_available(self, order):
        order.sudo().write({'delivery_carrier_desc': ''})
        if self.is_category:
            self.ensure_one()
            self = self.sudo()
            order = order.sudo()
            categ_ids = set([rule.categ_ids for rule in self.price_rule_ids])
            delivery_carrier_price = 0
            if not categ_ids:
                raise UserError(_("No price rule matching this order; delivery cost cannot be computed."))
            for categ in categ_ids:
                total = weight = volume = quantity = 0
                total_delivery = 0.0
                for line in order.order_line.filtered(lambda l: l.product_id.categ_id.id in categ.ids):
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
                    total += (line.price_subtotal + line.price_tax or 0.0) - total_delivery
                total = self._compute_currency(order, total, 'pricelist_to_company')
                if order.order_line.filtered(lambda l: l.product_id.categ_id.id in categ.ids):
                    delivery_carrier_price += self._get_price_from_order_picking(total, weight, volume, quantity, categ, order)
        else:
            delivery_carrier_price = super(DeliveryCarrier, self)._get_price_available(order)
        return delivery_carrier_price

    def _get_price_from_order_picking(self, total, weight, volume, quantity, categ_ids, order):
        price = 0.0
        criteria_found = False
        price_dict = self._get_price_dict(total, weight, volume, quantity)
        if self.free_over and total >= self.amount:
            return 0
        for line in self.price_rule_ids.filtered(lambda rule: not (categ_ids - rule.categ_ids)):
            test = safe_eval(line.variable + line.operator + str(line.max_value), price_dict)
            if test:
                price = line.list_base_price + line.list_price * price_dict[line.variable_factor]
                criteria_found = True
                so_description = order.delivery_carrier_desc + (line.description or '') + ': ' + str(price and order.currency_id.symbol or '') + (price and str(price) or 'Free')
                order.write({'delivery_carrier_desc': so_description + ', '})
                break
        if not criteria_found:
            raise UserError(_("No price rule matching this order; delivery cost cannot be computed."))
        return price
