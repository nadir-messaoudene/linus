# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from functools import partial
from itertools import count, groupby
import json

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.osv import expression
from odoo.tools import float_is_zero, html_keep_url, is_html_empty


class SaleOrder(models.Model):
    _inherit = "sale.order"

    delivery_status = fields.Selection([
        ('none', ''),
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('push_3pl', 'Pushed to 3PL'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
        ], string='Delivery Status', default='none', compute='_get_delivery_status', store=True)
    count_backorder = fields.Integer('Back Orders Count', compute='_get_delivery_status', store=True)

    last_carrier_tracking_ref = fields.Char(string='Tracking Reference',compute='_get_delivery_tracking', store=True)

    @api.depends('picking_ids.state')
    def _get_delivery_status(self):
        print('_get_delivery_status')
        for order in self:
            pickings = order.picking_ids.filtered(lambda l: l.picking_type_id.code != 'internal')
            backorders = pickings.backorder_ids
            pickings = sorted(pickings, key=lambda x: x.id)
            if len(pickings) > 0:
                order.delivery_status = pickings[-1].state
            else: 
                order.delivery_status = 'none'
            
            order.count_backorder = len(backorders)
            

    @api.depends('picking_ids.carrier_tracking_ref')
    def _get_delivery_tracking(self):
        for order in self:
            pickings = order.picking_ids.filtered(lambda l: l.picking_type_id.code != 'internal')
            if len(pickings) > 0:
                order.last_carrier_tracking_ref = pickings[-1].carrier_tracking_ref
            else: 
                order.last_carrier_tracking_ref = ''

    def action_update(self):
        to_update = self.env['sale.order'].search([])
        if not to_update:
            return
        for rec in to_update:
            rec._get_delivery_tracking()

#INHERTI PRICELIST for LINUS PROMOTION    
    @api.onchange('order_line')
    def _onchange_order_line_discount(self):
        for line in self.order_line:
            line._onchange_discount()

class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"
    @api.depends('applied_on', 'categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
        'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge')
    def _get_pricelist_item_name_price(self):
        for item in self:
            if item.categ_id and item.applied_on == '2_product_category':
                item.name = _("Category: %s - Min. Quantity: %s") % (item.categ_id.display_name, item.min_quantity)
            elif item.product_tmpl_id and item.applied_on == '1_product':
                item.name = _("Product: %s") % (item.product_tmpl_id.display_name)
            elif item.product_id and item.applied_on == '0_product_variant':
                item.name = _("Variant: %s") % (item.product_id.with_context(display_default_code=False).display_name)
            else:
                item.name = _("All Products")

            if item.compute_price == 'fixed':
                item.price = formatLang(item.env, item.fixed_price, monetary=True, dp="Product Price", currency_obj=item.currency_id)
            elif item.compute_price == 'percentage':
                item.price = _("%s %% discount", item.percent_price)
            else:
                item.price = _("%(percentage)s %% discount and %(price)s surcharge", percentage=item.price_discount, price=item.price_surcharge)

    #Update Min_Quantity with Combination for Comparision
    def min_quantity_updated(self):
        min_quantity_updated = self.min_quantity
        #case: category in combine but not apply by quantity
        temp = 0
        combination_obj = self.pricelist_id.combination_ids.search([('item_id', '=', self.id)])
        if combination_obj:
            combination = self.pricelist_id.combination_ids.search([('combine_number', '=', combination_obj.combine_number)])
            for item in combination:
                temp += item.item_id.min_quantity
        if temp > 0:
            return temp
        return min_quantity_updated

    def _is_applicable_for(self, product, qty_in_product_uom):
        self.ensure_one()
        product.ensure_one()
        res = True

        is_product_template = product._name == 'product.template'
        if self.min_quantity:
            if self.pricelist_id.apply_over and (product.categ_id in self.pricelist_id.combination_ids.item_id.categ_id or product.categ_id in self.pricelist_id.combination_ids.item_id.categ_id.child_id):
                self_min_quantity_updated = self.min_quantity_updated()
                if qty_in_product_uom < self_min_quantity_updated:
                    res = False
            else:
                if qty_in_product_uom < self.min_quantity:
                    res = False

        elif self.categ_id:
            # Applied on a specific category
            cat = product.categ_id
            while cat:
                if cat.id == self.categ_id.id:
                    break
                cat = cat.parent_id
            if not cat:
                res = False
        else:
            # Applied on a specific product template/variant
            if is_product_template:
                if self.product_tmpl_id and product.id != self.product_tmpl_id.id:
                    res = False
                elif self.product_id and not (
                    product.product_variant_count == 1
                    and product.product_variant_id.id == self.product_id.id
                ):
                    # product self acceptable on template if has only one variant
                    res = False
            else:
                if self.product_tmpl_id and product.product_tmpl_id.id != self.product_tmpl_id.id:
                    res = False
                elif self.product_id and product.id != self.product_id.id:
                    res = False

        return res
class PricelistItemCombination(models.Model):
    _name = "product.pricelist.item.combination"
    _order = 'combine_number ASC'

    pricelist_item_domain = fields.Char(compute='compute_category_domain', string="Pricelist Domain", readonly=True, store=False)
    item_id = fields.Many2one('product.pricelist.item', 'Item')
    combine_number = fields.Integer('Combine Number')
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', ondelete='cascade')

    @api.depends('pricelist_id')
    def compute_category_domain(self):
        for rec in self:
            if rec._context.get('default_pricelist_id', False):
                pricelist = rec.env['product.pricelist'].browse(rec._context.get('default_pricelist_id'))
                items = rec.env['product.pricelist.item'].search([('pricelist_id', '=', pricelist.id)])
                rec.pricelist_item_domain = json.dumps([('id', 'in', items.ids)])
            else:
                rec.pricelist_item_domain = json.dumps([('id', 'in', [])])

class Pricelist(models.Model):
    _inherit = "product.pricelist"

    apply_over = fields.Boolean('Apply Over', default=False)
    combination_ids = fields.One2many('product.pricelist.item.combination', 'pricelist_id', 'Combination')

    def write(self, vals):
        res = super(Pricelist, self).write(vals)
        if self.combination_ids:
            self.check_combine_constraint(self.combination_ids)
        return res

    def check_combine_constraint(self, combination_ids):
        if len(combination_ids) > 0:
            combine_number_list = []
            combine_item_list = []
            for combine in combination_ids:
                if combine.combine_number not in combine_number_list:
                    combine_number_list.append(combine.combine_number)
                if combine.item_id not in combine_item_list:
                    combine_item_list.append(combine.item_id)
            
            for combine_number in combine_number_list:
                #One Combine Number exists more than two rules
                check_detail_by_combine_number = combination_ids.filtered(lambda l: l.combine_number == combine_number)
                if len(check_detail_by_combine_number) < 2:
                    raise UserError('Please re-check the combination. Note: One Combine Number exists more than two rules.')
                #One Combine Number does not contain same rules.
                for combine_item in combine_item_list:
                    check_detail_by_combine_number_item = check_detail_by_combine_number.filtered(lambda l: l.item_id == combine_item)
                    if len(check_detail_by_combine_number_item) >= 2:
                        raise UserError('Please re-check the combination. Note: One Combine Number does not contain same rules.')
            #One Rule exits only one Combine Number.
            for combine_item in combine_item_list:
                check_detail_by_item = combination_ids.filtered(lambda l: l.item_id == combine_item)
                if len(check_detail_by_item) > 1:
                    raise UserError('Please re-check the combination. Note: One Rule exits only one Combine Number.')

        return True
    
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange('product_id', 'price_unit', 'product_uom', 'product_uom_qty', 'tax_id')
    def _onchange_discount(self):
        print("_onchange_discount")
        def combine_applied(order_lines, categories):
            if self.product_id.categ_id in categories or self.product_id.categ_id in categories.child_id:
                return True
            return False

        def calculate_product_qty(order_lines, pricelist=False, combine_applied=False):
            qty = 0
            if pricelist.combination_ids and combine_applied:
                for order_line in order_lines:
                   if order_line.product_id.categ_id in pricelist.combination_ids.item_id.categ_id or order_line.product_id.categ_id in pricelist.combination_ids.item_id.categ_id.child_id:
                        qty += order_line.product_uom_qty
            else:
                for order_line in order_lines:
                    if order_line.product_id.categ_id == self.product_id.categ_id or order_line.product_id.categ_id.parent_id == self.product_id.categ_id.parent_id:
                        qty += order_line.product_uom_qty
            return qty

        if not (self.product_id and self.product_uom and
                self.order_id.partner_id and self.order_id.pricelist_id and
                self.order_id.pricelist_id.discount_policy == 'without_discount' and
                self.env.user.has_group('product.group_discount_per_so_line')):
            return

        self.discount = 0.0
        qty = self.product_uom_qty
        if self.order_id.pricelist_id.apply_over:
            qty = calculate_product_qty(self.order_id._get_update_prices_lines(), 
                                        self.order_id.pricelist_id,
                                        combine_applied(self.order_id._get_update_prices_lines(), self.order_id.pricelist_id.combination_ids.item_id.categ_id))

        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id,
            quantity=qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id,
            fiscal_position=self.env.context.get('fiscal_position')
        )


        product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order, uom=self.product_uom.id)

        price, rule_id = self.order_id.pricelist_id.with_context(product_context).get_product_price_rule(self.product_id, qty or 1.0, self.order_id.partner_id)
        new_list_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.product_uom_qty, self.product_uom, self.order_id.pricelist_id.id)

        if new_list_price != 0:
            if self.order_id.pricelist_id.currency_id != currency:
                # we need new_list_price in the same currency as price, which is in the SO's pricelist's currency
                new_list_price = currency._convert(
                    new_list_price, self.order_id.pricelist_id.currency_id,
                    self.order_id.company_id or self.env.company, self.order_id.date_order or fields.Date.today())
            discount = (new_list_price - price) / new_list_price * 100
            if (discount > 0 and new_list_price > 0) or (discount < 0 and new_list_price < 0):
                self.discount = discount