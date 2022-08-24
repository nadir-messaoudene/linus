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
    merge_rule_by_categ = fields.Boolean('Merge Rule by Category', default=False)
    free_over_qty = fields.Boolean('Free if order quantity is above',
                               help="If the order total quantity (shipping excluded) is above or equal to this value, the customer benefits from a free shipping",
                               default=False)
    quantity = fields.Float(string='Quantity',
                          help="Quantity of the order to benefit from a free shipping, expressed in the company currency")

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

        if self.is_category:

            return self._get_price_order_from_picking(total, weight, volume, quantity, order)
        return self._get_price_from_picking(total, weight, volume, quantity)

    def _get_quantity_from_order(self, order, categ_ids):
        total_qty = 0.0
        categ_ids = [categ_id.id for categ_id in categ_ids]
        for line in order.order_line.filtered(lambda l: l.product_id.categ_id.id in categ_ids):
            print('>>>>>>>>>>>>>INSIDE1 _get_quantity_from_order', line.product_id.name)
            total_qty += line.product_uom_qty
        return total_qty

    def _get_categs_from_rule(self, price_rule_ids):
        rule_line_categ_dicts = {}
        rule_line_ids = [line.id for line in price_rule_ids]
        if len(rule_line_ids) > 1:
            rule_line_categ_ids = self.env['delivery.price.rule.categ.price'].sudo().search([('rule_id', 'in', rule_line_ids)])
            remove_dupl_rule_line_categ_ids = set([rule_line_categ_id.categ_id for rule_line_categ_id in rule_line_categ_ids])
            rule_line_categ_dicts = [{'formula': rule_line_categ_id.rule_id.formula, 'categ_id': rule_line_categ_id.categ_id, 'list_price': rule_line_categ_id.list_price} for rule_line_categ_id in rule_line_categ_ids]

            # print('rule_line_categ_dict', rule_line_categ_dict)
            # print('rule_line_categ_dict', remove_dupl_rule_line_categ_ids)
            # print('rule_line_categ_dict', rule_line_categ_dict)
            # categ_ids = [l_categ_id for l_categ_id in line.categ_ids]
            # for categ_id in categ_ids:
            #     rule_categ_ids.append(categ_id)
        # else:
        #     rule_categ_ids.append(line.categ_ids)
        return rule_line_categ_dicts, remove_dupl_rule_line_categ_ids

    def _get_price_order_from_picking(self, total, weight, volume, quantity, order):
        price = 0.0
        if self.free_over and total >= self.amount:
            return 0
        if self.is_category:
            # rule_line_categ_dicts, remove_dupl_rule_line_categ_ids = self._get_categs_from_rule(self.price_rule_ids)
            # print('rule_line_categ_dicts', rule_line_categ_dicts)
            # print('remove_dupl_rule_line_categ_ids', remove_dupl_rule_line_categ_ids)
            # print('_get_quantity_from_order', self._get_quantity_from_order(order, remove_dupl_rule_line_categ_ids))
            # total_order_qty = self._get_quantity_from_order(order, remove_dupl_rule_line_categ_ids)
            # for rule_line_categ_dict in rule_line_categ_dicts:
            #     print('rule_line_categ_dict', rule_line_categ_dict)
            for rule_id in self.price_rule_ids:
                print('rule_id', rule_id)
                total_qty = 0.0
                for rule_line in rule_id.categ_price_ids:
                    print('>>>>>>>>>', rule_line.rule_id.formula)
                    categ_ids = [line.categ_id for line in rule_line]
                    total_qty += self._get_quantity_from_order(order, categ_ids)
                print('>>>>>>>>> total_qty', total_qty)
                quantity = total_qty
                price = self._get_amount_from_order(total, weight, volume, quantity, rule_id, order)
                print('price', price)




        # self._get_categs_from_rule(self.price_rule_ids, total, weight, volume, quantity)


        # if self.is_category and order:
        #     for rule_categ_id in rule_categ_ids:
        #         child_categ_
        #
        #         total_qty += self._get_quantity_from_order(order, line.categ_ids.ids)
        #         if total_qty >= line.max_value and line.list_price == 0:
        #             print('TRUEEEE', total_qty)
        #             return 0
        #     rule_ids = [line for line in self.price_rule_ids.filtered(lambda r: len(r.categ_ids) == 1)]
        #     categ_ids = list(set([rule_id.categ_ids for rule_id in rule_ids]))
        #     print('categ_ids', categ_ids)
        #     total_other_qty = self._get_quantity_from_order(order, categ_ids)
        #     print('total_other_qty', total_other_qty)
        #     line_catog_ids = [line.product_id.categ_id for line in order.order_line if not line.is_delivery]
        #     for line_catog_id in line_catog_ids:
        #         print('priceprice0', price)
        #         for rule_id in rule_ids:
        #             total_qty = self._get_quantity_from_order(order, [line_catog_id.id])
        #             total_amount = self._get_total_amount_from_order(order, [line_catog_id.id])
        #             print('total_qty', total_qty, total_amount)
        #             if rule_id.categ_ids in line_catog_id and total_qty > 0 and total_amount > 0:
        #                 quantity = total_qty
        #                 total = total_amount
        #                 price += self._get_amount_from_order(total, weight, volume, quantity, rule_id, order)

        return price

    def _get_amount_from_order(self, total, weight, volume, quantity, rule_id, order):
        price = 0.0
        price_dict = self._get_price_dict(total, weight, volume, quantity)
        print('::::::::::;;', (rule_id.formula, price_dict))
        test = safe_eval(rule_id.formula, price_dict)
        order.write({'delivery_carrier_desc': ''})
        if test:
            price = rule_id.list_base_price + rule_id.list_price * price_dict[rule_id.variable_factor]
            so_description = order.delivery_carrier_desc + (rule_id.description or '') + ': ' + str(
                price and order.currency_id.symbol or '') + (price and str(price) or 'Free')
            # order.write({'delivery_carrier_desc': so_description + ', '})
        return price

    # def _get_categ_from_rule(self, price_rule_ids):
    #     rule_categ_ids = []
    #     for line in price_rule_ids:
    #         if len(line.categ_ids) > 1:
    #             categ_ids = [l_categ_id for l_categ_id in line.categ_ids]
    #             for categ_id in categ_ids:
    #                 rule_categ_ids.append(categ_id)
    #         else:
    #             rule_categ_ids.append(line.categ_ids)
    #     return list(set(rule_categ_ids))
    #
    # def _get_rule(self, price_rule_ids, total, weight, volume, quantity):
    #     print('rule_categ_ids', quantity, price_rule_ids)
    #     price_dict = self._get_price_dict(total, weight, volume, quantity)
    #     for price_rule_id in price_rule_ids:
    #         print('MMMMMMMMMMMMMMMMM', safe_eval(price_rule_id.formula, price_dict))
    #         if safe_eval(price_rule_id.formula, price_dict):
    #             print('MMMMMMMMMMMMMMMMM', price_rule_id.name)
    #
    #         # if quantity >= price_rule_id.max_value and quantity <= price_rule_id.max_value:
    #
    #
    #     return True
    #
    # def _get_price_order_from_picking(self, total, weight, volume, quantity, order):
    #     price = 0.0
    #     if self.free_over and total >= self.amount:
    #         return 0
    #     rule_categ_ids = self._get_categ_from_rule(self.price_rule_ids)
    #     print('rule_categ_ids', quantity)
    #
    #     self._get_rule(self.price_rule_ids, total, weight, volume, quantity)
    #
    #
    #     # if self.is_category and order:
    #     #     for rule_categ_id in rule_categ_ids:
    #     #         child_categ_
    #     #
    #     #         total_qty += self._get_quantity_from_order(order, line.categ_ids.ids)
    #     #         if total_qty >= line.max_value and line.list_price == 0:
    #     #             print('TRUEEEE', total_qty)
    #     #             return 0
    #     #     rule_ids = [line for line in self.price_rule_ids.filtered(lambda r: len(r.categ_ids) == 1)]
    #     #     categ_ids = list(set([rule_id.categ_ids for rule_id in rule_ids]))
    #     #     print('categ_ids', categ_ids)
    #     #     total_other_qty = self._get_quantity_from_order(order, categ_ids)
    #     #     print('total_other_qty', total_other_qty)
    #     #     line_catog_ids = [line.product_id.categ_id for line in order.order_line if not line.is_delivery]
    #     #     for line_catog_id in line_catog_ids:
    #     #         print('priceprice0', price)
    #     #         for rule_id in rule_ids:
    #     #             total_qty = self._get_quantity_from_order(order, [line_catog_id.id])
    #     #             total_amount = self._get_total_amount_from_order(order, [line_catog_id.id])
    #     #             print('total_qty', total_qty, total_amount)
    #     #             if rule_id.categ_ids in line_catog_id and total_qty > 0 and total_amount > 0:
    #     #                 quantity = total_qty
    #     #                 total = total_amount
    #     #                 price += self._get_amount_from_order(total, weight, volume, quantity, rule_id, order)
    #
    #     return price

    # def _get_price_order_from_picking(self, total, weight, volume, quantity, order):
    #     price = 0.0
    #     if self.free_over and total >= self.amount:
    #         return 0
    #     if self.is_category and order:
    #         for line in self.price_rule_ids.filtered(lambda r: len(r.categ_ids) > 1):
    #             total_qty = self._get_quantity_from_order(order, line.categ_ids.ids)
    #             if total_qty >= line.max_value and line.list_price == 0:
    #                 print('TRUEEEE', total_qty)
    #                 return 0
    #         rule_ids = [line for line in self.price_rule_ids.filtered(lambda r: len(r.categ_ids) == 1)]
    #         categ_ids = list(set([rule_id.categ_ids for rule_id in rule_ids]))
    #         print('categ_ids', categ_ids)
    #         total_other_qty = self._get_quantity_from_order(order, categ_ids)
    #         print('total_other_qty', total_other_qty)
    #         line_catog_ids = [line.product_id.categ_id for line in order.order_line if not line.is_delivery]
    #         for line_catog_id in line_catog_ids:
    #             print('priceprice0', price)
    #             for rule_id in rule_ids:
    #                 total_qty = self._get_quantity_from_order(order, [line_catog_id.id])
    #                 total_amount = self._get_total_amount_from_order(order, [line_catog_id.id])
    #                 print('total_qty', total_qty, total_amount)
    #                 if rule_id.categ_ids in line_catog_id and total_qty > 0 and total_amount > 0:
    #                     quantity = total_qty
    #                     total = total_amount
    #                     price += self._get_amount_from_order(total, weight, volume, quantity, rule_id, order)
    #
    #         return price
    #
    # def _get_quantity_from_order(self, order, categ_ids):
    #     total_qty = 0.0
    #     for line in order.order_line.filtered(lambda l: l.product_id.categ_id.id in categ_ids):
    #         print('>>>>>>>>>>>>>INSIDE1 _get_quantity_from_order', line.product_id.name)
    #         total_qty += line.product_uom_qty
    #     return total_qty
    #
    # def _get_total_amount_from_order(self, order, categ_ids):
    #     total_amount = 0.0
    #     for line in order.order_line.filtered(lambda l: l.product_id.categ_id.id in categ_ids):
    #         # print('>>>>>>>>>>>>>INSIDE1 _get_quantity_from_order', line.product_id.name)
    #         total_amount += line.price_subtotal
    #     return total_amount
    #
    # def _get_amount_from_order(self, total, weight, volume, quantity, rule_id, order):
    #     price = 0.0
    #     price_dict = self._get_price_dict(total, weight, volume, quantity)
    #     print('::::::::::;;', (rule_id.formula, price_dict))
    #     test = safe_eval(rule_id.formula, price_dict)
    #     order.write({'delivery_carrier_desc': ''})
    #     if test:
    #         price = rule_id.list_base_price + rule_id.list_price * price_dict[rule_id.variable_factor]
    #         so_description = order.delivery_carrier_desc + (rule_id.description or '') + ': ' + str(
    #             price and order.currency_id.symbol or '') + (price and str(price) or 'Free')
    #         # order.write({'delivery_carrier_desc': so_description + ', '})
    #     return price

    # def _get_price_available(self, order):
    #     self.ensure_one()
    #     self = self.sudo()
    #     order = order.sudo()
    #     total = weight = volume = quantity = 0
    #     total_delivery = 0.0
    #     line_catog_ids = [line.product_id.categ_id for line in order.order_line if not line.is_delivery]
    #     for line_catog_id in line_catog_ids:
    #         for price_rule_id in self.price_rule_ids:
    #
    #         apply_rule_ids = [rule_id for rule_id in self.price_rule_ids if rule_id.categ_id.id == line_catog_id.id]
    #     # for price_rule_id in self.price_rule_ids:
    #     #     print('price_rule_id.categ_ids.ids', price_rule_id.categ_ids.ids)
    #     #     print('line_catog_ids', line_catog_ids)
    #     #     if price_rule_id.categ_ids.ids == line_catog_ids:
    #     #         apply_rule_ids.append(price_rule_id.id)
    #     print('apply_rule_ids',line_catog_ids, self.price_rule_ids, apply_rule_ids)
    #     total_order_qty = sum([line.product_uom_qty for line in order.order_line if not line.is_delivery])
    #     if self.is_category:
    #         if self.free_over_qty and total_order_qty >= self.quantity:
    #             for line in order.order_line:
    #                 print('line categ', line.product_categ_id.name)
    #                 if line.state == 'cancel':
    #                     continue
    #                 if line.is_delivery:
    #                     total_delivery += line.price_total
    #                 if not line.product_id or line.is_delivery:
    #                     continue
    #                 if line.product_id.type == "service":
    #                     continue
    #                 qty = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
    #                 weight += (line.product_id.weight or 0.0) * qty
    #                 volume += (line.product_id.volume or 0.0) * qty
    #                 quantity += qty
    #             total = (order.amount_total or 0.0) - total_delivery
    #
    #             total = self._compute_currency(order, total, 'pricelist_to_company')
    #             total_order_qty = sum([line.product_uom_qty for line in order.order_line if not line.is_delivery])
    #             return self._get_price_from_picking(total, weight, volume, quantity, total_order_qty)
    #         else:
    #             delivery_carrier_price = self._get_price_available_by_categ(order)
    #     else:
    #         delivery_carrier_price = super(DeliveryCarrier, self)._get_price_available(order)
    #     return delivery_carrier_price
    #
    # def _get_price_from_picking(self, total, weight, volume, quantity, total_order_qty):
    #     price = 0.0
    #     criteria_found = False
    #     price_dict = self._get_price_dict(total, weight, volume, quantity)
    #     if self.free_over and total >= self.amount:
    #         return 0
    #     print('quantity', quantity)
    #     if self.free_over_qty and total_order_qty >= self.quantity:
    #         return 0
    #     for line in self.price_rule_ids:
    #         # test = safe_eval(line.variable + line.operator + str(line.max_value), price_dict)
    #         test = safe_eval(line.formula, price_dict)
    #         if test:
    #             price = line.list_base_price + line.list_price * price_dict[line.variable_factor]
    #             criteria_found = True
    #             break
    #     if not criteria_found:
    #         raise UserError(_("No price rule matching this order; delivery cost cannot be computed."))
    #     return price
    # def _get_price_available_by_categ(self, order):
    #     categ_ids = set([rule.categ_ids for rule in self.price_rule_ids])
    #     delivery_carrier_price = 0
    #     delivery_carrier_ddetails = []
    #     if not categ_ids:
    #         raise UserError(_("No price rule matching this order; delivery cost cannot be computed."))
    #     for categ in categ_ids:
    #         total = weight = volume = quantity = 0
    #         total_delivery = 0.0
    #         for line in order.order_line.filtered(lambda l: l.product_id.categ_id.id in categ.ids):
    #             if line.state == 'cancel':
    #                 continue
    #             if line.is_delivery:
    #                 total_delivery += line.price_total
    #             if not line.product_id or line.is_delivery:
    #                 continue
    #             if line.product_id.type == "service":
    #                 continue
    #             qty = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
    #             weight += (line.product_id.weight or 0.0) * qty
    #             volume += (line.product_id.volume or 0.0) * qty
    #             quantity += qty
    #             total += (line.price_subtotal + line.price_tax or 0.0) - total_delivery
    #         total = self._compute_currency(order, total, 'pricelist_to_company')
    #         if order.order_line.filtered(lambda l: l.product_id.categ_id.id in categ.ids):
    #             delivery_carrier_price += self._get_price_from_order_picking(total, weight, volume, quantity, categ, order)
    #     #         delivery_carrier_price, delivery_carrier_desc = self._get_price_from_order_picking(total, weight, volume, quantity,
    #     #                                                                      categ, order)
    #     #         print('delivery_carrier_price >>>>', delivery_carrier_price)
    #     #         print('delivery_carrier_desc >>>>', delivery_carrier_desc)
    #     #         delivery_carrier_price += delivery_carrier_price
    #     #         delivery_carrier_ddetails.append(delivery_carrier_desc)
    #     # print('delivery_carrier_ddetails', delivery_carrier_ddetails)
    #     return delivery_carrier_price
    #
    #
    # def _get_price_from_order_picking(self, total, weight, volume, quantity, categ_ids, order):
    #     price = 0.0
    #     criteria_found = False
    #     so_description_list = []
    #     so_description = ''
    #     price_dict = self._get_price_dict(total, weight, volume, quantity)
    #     if self.free_over and total >= self.amount:
    #         return 0
    #     for line in self.price_rule_ids.filtered(lambda rule: not (categ_ids - rule.categ_ids)):
    #         # test = safe_eval(line.variable + line.operator + str(line.max_value), price_dict)
    #         test = safe_eval(line.formula, price_dict)
    #
    #         if test:
    #             price = line.list_base_price + line.list_price * price_dict[line.variable_factor]
    #             criteria_found = True
    #             # print('so_description', order.delivery_carrier_desc)
    #             so_description = ((line.description or '') + ': ' + str(
    #                 price and order.currency_id.symbol or '') + (price and str(price) or 'Free'))
    #
    #             # print('so_description', so_description)
    #             # order.write({'delivery_carrier_desc': so_description + ', '})
    #             break
    #         so_description_list.append(so_description)
    #     print('so_description_list', so_description_list)
    #     # order.write({'delivery_carrier_desc': so_description + ', '})
    #     if not criteria_found:
    #         raise UserError(_("No price rule matching this order; delivery cost cannot be computed."))
    #     return price
    #     # return price, so_description


        # def _get_price_available(self, order):
    #     self.ensure_one()
    #     self = self.sudo()
    #     order = order.sudo()
    #     total = weight = volume = quantity = 0
    #     delivery_carrier_price = 0
    #     total_delivery = 0.0
    #     for line in order.order_line:
    #         if line.state == 'cancel':
    #             continue
    #         if line.is_delivery:
    #             total_delivery += line.price_total
    #         if not line.product_id or line.is_delivery:
    #             continue
    #         if line.product_id.type == "service":
    #             continue
    #         qty = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
    #         weight += (line.product_id.weight or 0.0) * qty
    #         volume += (line.product_id.volume or 0.0) * qty
    #         quantity += qty
    #     total = (order.amount_total or 0.0) - total_delivery
    #
    #     total = self._compute_currency(order, total, 'pricelist_to_company')
    #
    #     return self._get_price_from_picking(total, weight, volume, quantity, order)
    #
    # def _get_price_from_picking(self, total, weight, volume, quantity, order):
    #     price = 0.0
    #     criteria_found = False
    #     price_dict = self._get_price_dict(total, weight, volume, quantity)
    #     if self.free_over and total >= self.amount:
    #         return 0
    #     if self.free_over and quantity >= self.amount:
    #         return 0
    #     for line in self.price_rule_ids:
    #         if line.formula:
    #             test = safe_eval(line.variable + line.operator + str(line.max_value), price_dict)
    #             # test = safe_eval(line.formula, price_dict)
    #             if test:
    #                 print('testtest', line.name)
    #                 price = line.list_base_price + line.list_price * price_dict[line.variable_factor]
    #                 criteria_found = True
    #                 break
    #     if not criteria_found:
    #         raise UserError(_("No price rule matching this order; delivery cost cannot be computed."))
    #
    #     return price




        #     test = safe_eval(line.variable + line.operator + str(line.max_value), price_dict)
        #     if test:
        #         price = line.list_base_price + line.list_price * price_dict[line.variable_factor]
        #         criteria_found = True
        #         break
        # if not criteria_found:
        #     raise UserError(_("No price rule matching this order; delivery cost cannot be computed."))
        #
        # return price

    # def _get_price_available(self, order):
    #     order.sudo().write({'delivery_carrier_desc': ''})
    #     if self.is_category:
    #         self.ensure_one()
    #         self = self.sudo()
    #         order = order.sudo()
    #         total = weight = volume = quantity = 0
    #         total_delivery = 0.0
    #         delivery_carrier_price = 0
    #         categ_ids = set([rule.categ_ids for rule in self.price_rule_ids])
    #
    #         order_line_catag_ids = [line.product_id.categ_id.id for line in order.order_line if not line.is_delivery]
    #
    #         # categ_ids = [rule.categ_ids for rule in self.price_rule_ids]
    #         apply_rule_to_multi_categ_ids = [rule for rule in self.price_rule_ids]
    #         print('apply_to_multi_categ_ids', apply_rule_to_multi_categ_ids)
    #         for line in order.order_line:
    #             for apply_to_multi_categ_id in apply_rule_to_multi_categ_ids:
    #                 if line.product_id.categ_id.id in apply_to_multi_categ_id.categ_ids.ids:
    #                     print('INSIDE')
    #                     if line.state == 'cancel':
    #                         continue
    #                     if line.is_delivery:
    #                         total_delivery += line.price_total
    #                     if not line.product_id or line.is_delivery:
    #                         continue
    #                     if line.product_id.type == "service":
    #                         continue
    #                     qty = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
    #                     weight += (line.product_id.weight or 0.0) * qty
    #                     volume += (line.product_id.volume or 0.0) * qty
    #                     quantity += qty
    #                     total += (line.price_subtotal + line.price_tax or 0.0) - total_delivery
    #                 total = self._compute_currency(order, total, 'pricelist_to_company')
    #         # delivery_carrier_price += self._get_price_from_order_picking(total, weight, volume, quantity, order)
    #         delivery_carrier_price += self._get_price_on_from_picking(total, weight, volume, quantity, order)
    #         print('quantity', quantity)
    #
    #         print('order_line_catag_ids', order_line_catag_ids, rule_ids)
    #         delivery_carrier_price = 0
    #         if not rule_ids:
    #             raise UserError(_("No price rule matching this order; delivery cost cannot be computed."))
    #     #     for categ in categ_ids:
    #     #         total = weight = volume = quantity = 0
    #     #         total_delivery = 0.0
    #     #         order_line_catag_ids = [line.product_id.categ_id.id for line in order.order_line if not line.is_delivery]
    #     #         # rule_ids = self.price_rule_ids
    #     #         rule_ids = []
    #     #         for rule in self.price_rule_ids:
    #     #             if rule.categ_ids.ids in order_line_catag_ids:
    #     #                 print('rule>>>>>', rule)
    #     #                 rule_ids.append(rule)
    #     #
    #     #         print('order_line_catag_ids', order_line_catag_ids, rule_ids)
    #     #         for line in order.order_line.filtered(lambda l: l.product_id.categ_id.id in categ.ids):
    #     #             if line.state == 'cancel':
    #     #                 continue
    #     #             if line.is_delivery:
    #     #                 total_delivery += line.price_total
    #     #             if not line.product_id or line.is_delivery:
    #     #                 continue
    #     #             if line.product_id.type == "service":
    #     #                 continue
    #     #             qty = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
    #     #             weight += (line.product_id.weight or 0.0) * qty
    #     #             volume += (line.product_id.volume or 0.0) * qty
    #     #             quantity += qty
    #     #             total += (line.price_subtotal + line.price_tax or 0.0) - total_delivery
    #     #         total = self._compute_currency(order, total, 'pricelist_to_company')
    #     #     if order.order_line.filtered(lambda l: l.product_id.categ_id.id in categ.ids):
    #     #
    #     #         delivery_carrier_price += self._get_price_from_order_picking(total, weight, volume, quantity, categ, order)
    #     # else:
    #     #     delivery_carrier_price = super(DeliveryCarrier, self)._get_price_available(order)
    #     return delivery_carrier_price
    #
    # def _get_price_on_from_picking(self, total, weight, volume, quantity, order):
    #     price = 0.0
    #     criteria_found = False
    #     price_dict = self._get_price_dict(total, weight, volume, quantity)
    #     if self.free_over and total >= self.amount:
    #         return 0
    #     for line in self.price_rule_ids:
    #         test = safe_eval(line.variable + line.operator + str(line.max_value), price_dict)
    #         if test:
    #             price = line.list_base_price + line.list_price * price_dict[line.variable_factor]
    #             criteria_found = True
    #             so_description = order.delivery_carrier_desc + (line.description or '') + ': ' + str(
    #                 price and order.currency_id.symbol or '') + (price and str(price) or 'Free')
    #             order.write({'delivery_carrier_desc': so_description + ', '})
    #             break
    #     if not criteria_found:
    #         raise UserError(_("No price rule matching this order; delivery cost cannot be computed."))
    #
    #     return price
    #
    # # def _get_price_available(self, order):
    # #     order.sudo().write({'delivery_carrier_desc': ''})
    # #     if self.is_category:
    # #         self.ensure_one()
    # #         self = self.sudo()
    # #         order = order.sudo()
    # #         categ_ids = set([rule.categ_ids for rule in self.price_rule_ids])
    # #         delivery_carrier_price = 0
    # #         if not categ_ids:
    # #             raise UserError(_("No price rule matching this order; delivery cost cannot be computed."))
    # #         for categ in categ_ids:
    # #             total = weight = volume = quantity = 0
    # #             total_delivery = 0.0
    # #             for line in order.order_line.filtered(lambda l: l.product_id.categ_id.id in categ.ids):
    # #                 if line.state == 'cancel':
    # #                     continue
    # #                 if line.is_delivery:
    # #                     total_delivery += line.price_total
    # #                 if not line.product_id or line.is_delivery:
    # #                     continue
    # #                 if line.product_id.type == "service":
    # #                     continue
    # #                 qty = line.product_uom._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
    # #                 weight += (line.product_id.weight or 0.0) * qty
    # #                 volume += (line.product_id.volume or 0.0) * qty
    # #                 quantity += qty
    # #                 total += (line.price_subtotal + line.price_tax or 0.0) - total_delivery
    # #             total = self._compute_currency(order, total, 'pricelist_to_company')
    # #             if order.order_line.filtered(lambda l: l.product_id.categ_id.id in categ.ids):
    # #                 delivery_carrier_price += self._get_price_from_order_picking(total, weight, volume, quantity, categ, order)
    # #     else:
    # #         delivery_carrier_price = super(DeliveryCarrier, self)._get_price_available(order)
    # #     return delivery_carrier_price
    #
    # # def _get_price_from_order_picking(self, total, weight, volume, quantity, categ_ids, order):
    # #     price = 0.0
    # #     criteria_found = False
    # #     price_dict = self._get_price_dict(total, weight, volume, quantity)
    # #     if self.free_over and total >= self.amount:
    # #         return 0
    # #     # for line in self.price_rule_ids.filtered(lambda rule: not (categ_ids - rule.categ_ids)):
    # #     for line in self.price_rule_ids:
    # #         print('line', line.name, quantity, (line.variable + line.operator + str(line.max_value), price_dict))
    # #         test = safe_eval(line.variable + line.operator + str(line.max_value), price_dict)
    # #         print('test', test)
    # #         if test:
    # #             price = line.list_base_price + line.list_price * price_dict[line.variable_factor]
    # #             criteria_found = True
    # #             so_description = order.delivery_carrier_desc + (line.description or '') + ': ' + str(
    # #                 price and order.currency_id.symbol or '') + (price and str(price) or 'Free')
    # #             order.write({'delivery_carrier_desc': so_description + ', '})
    # #             break
    # #     if not criteria_found:
    # #         raise UserError(_("No price rule matching this order; delivery cost cannot be computed."))
    # #     return price
    #
    # # def _get_price_from_order_picking(self, total, weight, volume, quantity, categ_ids, order):
    # #     price = 0.0
    # #     criteria_found = False
    # #     price_dict = self._get_price_dict(total, weight, volume, quantity)
    # #     if self.free_over and total >= self.amount:
    # #         return 0
    # #     print('quantity', quantity, categ_ids)
    # #     group_by_category_rule_ids = [rule for rule in self.price_rule_ids if rule.categ_id in categ_ids]
    # #     group_by_category_rule_names = [rule.name for rule in self.price_rule_ids if rule.categ_ids in categ_ids]
    # #     rule_to_check = [rule_id.id for rule_id in group_by_category_rule_ids if quantity >= rule_id.max_value]
    # #     if not rule_to_check:
    # #         rule_to_check = [rule_id.id for rule_id in group_by_category_rule_ids if quantity <= rule_id.max_value]
    # #     print('group_by_category_rule_names', group_by_category_rule_names)
    # #     print('group_by_category_rule_ids', group_by_category_rule_ids)
    # #
    # #     rule_to_check = self.env['delivery.price.rule'].browse(rule_to_check)
    # #     print('rule_to_check', rule_to_check)
    # #     for line in rule_to_check.filtered(lambda rule: not (categ_ids - rule.categ_id)):
    # #     # for line in self.price_rule_ids.filtered(lambda rule: not (categ_ids - rule.categ_ids)):
    # #         test = safe_eval(line.variable + line.operator + str(line.max_value), price_dict)
    # #         if test:
    # #             price = line.list_base_price + line.list_price * price_dict[line.variable_factor]
    # #             criteria_found = True
    # #             so_description = order.delivery_carrier_desc + (line.description or '') + ': ' + str(price and order.currency_id.symbol or '') + (price and str(price) or 'Free')
    # #             order.write({'delivery_carrier_desc': so_description + ', '})
    # #             break
    # #     if not criteria_found:
    # #         raise UserError(_("No price rule matching this order; delivery cost cannot be computed."))
    # #     return price
    #
