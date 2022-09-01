# -*- coding: utf-8 -*-
# Part of Syncoria. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PriceRule(models.Model):
    _inherit = "delivery.price.rule"

    categ_price_ids = fields.One2many('delivery.price.rule.categ.price', 'rule_id', string='Product Category')
    description = fields.Char()
    combine = fields.Selection([('and', 'and'), ('or', 'or')], required=False)
    variable_2 = fields.Selection(
        [('weight', 'Weight'), ('volume', 'Volume'), ('wv', 'Weight * Volume'), ('price', 'Price'),
         ('quantity', 'Quantity')], required=False)
    operator_2 = fields.Selection([('==', '='), ('<=', '<='), ('<', '<'), ('>=', '>='), ('>', '>')],
                                  required=False)
    max_value_2 = fields.Float('Maximum Value', required=False)
    combine_1 = fields.Selection([('and', 'and'), ('or', 'or')], required=False)
    variable_3 = fields.Selection(
        [('weight', 'Weight'), ('volume', 'Volume'), ('wv', 'Weight * Volume'), ('price', 'Price'),
         ('quantity', 'Quantity')], required=False)
    operator_3 = fields.Selection([('==', '='), ('<=', '<='), ('<', '<'), ('>=', '>='), ('>', '>')],
                                  required=False)
    max_value_3 = fields.Float('Maximum Value', required=False)
    formula = fields.Char(compute='_compute_formula', store=False)

    def _compute_formula(self):
        for rule in self:
            if not rule.combine and not rule.combine_1:
                formula = '%s %s %.02f' % (rule.variable, rule.operator, rule.max_value)
            elif rule.combine and not rule.combine_1:
                formula = '%s %s %.02f %s %s %s %.02f' \
                          % (rule.variable, rule.operator, rule.max_value, rule.combine,
                             rule.variable_2, rule.operator_2, rule.max_value_2)
            elif rule.combine and rule.combine_1:
                if (rule.combine == 'and' and rule.combine_1 == 'and') or \
                        (rule.combine == 'or' and rule.combine_1 == 'or'):
                    formula = '%s %s %.02f %s %s %s %.02f %s %s %s %.02f' \
                              % (rule.variable, rule.operator, rule.max_value, rule.combine,
                                 rule.variable_2, rule.operator_2, rule.max_value_2,
                                 rule.combine_1, rule.variable_3, rule.operator_3, rule.max_value_3)

                if rule.combine == 'or' and rule.combine_1 == 'and':
                    formula = '%s %s %.02f %s (%s %s %.02f %s %s %s %.02f)' \
                              % (rule.variable, rule.operator, rule.max_value, rule.combine,
                                 rule.variable_2, rule.operator_2, rule.max_value_2,
                                 rule.combine_1, rule.variable_3, rule.operator_3, rule.max_value_3)

                if rule.combine == 'and' and rule.combine_1 == 'or':
                    formula = '(%s %s %.02f %s %s %s %.02f) %s %s %s %.02f' \
                              % (rule.variable, rule.operator, rule.max_value, rule.combine,
                                 rule.variable_2, rule.operator_2, rule.max_value_2,
                                 rule.combine_1, rule.variable_3, rule.operator_3, rule.max_value_3)
            rule.formula = formula

    @api.onchange('combine')
    def on_change_combine(self):
        if not self.combine:
            self.variable_2 = ''
            self.operator_2 = ''
            self.max_value_2 = ''
            self.combine_1 = ''
            self.variable_3 = ''
            self.operator_3 = ''
            self.max_value_3 = ''

    @api.onchange('combine_1')
    def on_change_combine_1(self):
        if not self.combine_1:
            self.variable_3 = ''
            self.operator_3 = ''
            self.max_value_3 = ''

    def _compute_name(self):
        for rule in self:
            name = ''
            if not rule.combine and not rule.combine_1:
                name = 'if %s %s %.02f then' % (rule.variable, rule.operator, rule.max_value)
            elif rule.combine and not rule.combine_1:
                name = 'if %s %s %.02f %s %s %s %.02f then' \
                       % (rule.variable, rule.operator, rule.max_value, rule.combine,
                          rule.variable_2, rule.operator_2, rule.max_value_2)
            elif rule.combine and rule.combine_1:
                if (rule.combine == 'and' and rule.combine_1 == 'and') or \
                        (rule.combine == 'or' and rule.combine_1 == 'or'):
                    name = 'if %s %s %.02f %s %s %s %.02f %s %s %s %.02f then' \
                           % (rule.variable, rule.operator, rule.max_value, rule.combine,
                              rule.variable_2, rule.operator_2, rule.max_value_2,
                              rule.combine_1, rule.variable_3, rule.operator_3, rule.max_value_3)

                if rule.combine == 'or' and rule.combine_1 == 'and':
                    name = 'if %s %s %.02f %s (%s %s %.02f %s %s %s %.02f)then' \
                           % (rule.variable, rule.operator, rule.max_value, rule.combine,
                              rule.variable_2, rule.operator_2, rule.max_value_2,
                              rule.combine_1, rule.variable_3, rule.operator_3, rule.max_value_3)

                if rule.combine == 'and' and rule.combine_1 == 'or':
                    name = 'if (%s %s %.02f %s %s %s %.02f) %s %s %s %.02f then' \
                           % (rule.variable, rule.operator, rule.max_value, rule.combine,
                              rule.variable_2, rule.operator_2, rule.max_value_2,
                              rule.combine_1, rule.variable_3, rule.operator_3, rule.max_value_3)

            if rule.list_base_price and not rule.list_price:
                name = '%s fixed price %.02f' % (name, rule.list_base_price)
            elif rule.list_price and not rule.list_base_price:
                if rule.variable_factor not in ['add_weight', 'add_volume']:
                    name = '%s %.02f times %s' % (name, rule.list_price, rule.variable_factor)
                else:
                    if rule.variable_factor == 'add_weight':
                        variable_factor = 'Additional Weight'
                    else:
                        variable_factor = 'Additional Volume'
                    name = '%s %.02f times %s' % (name, rule.list_price, variable_factor)

            else:
                if rule.variable_factor not in ['add_weight', 'add_volume']:
                    name = '%s fixed price %.02f plus %.02f times %s' % (
                        name, rule.list_base_price, rule.list_price, rule.variable_factor)
                else:
                    if rule.variable_factor == 'add_weight':
                        variable_factor = 'Additional Weight'
                    else:
                        variable_factor = 'Additional Volume'
                    name = '%s fixed price %.02f plus %.02f times %s' % (
                        name, rule.list_base_price, rule.list_price, variable_factor)

            rule.name = name


class PriceRuleCateg(models.Model):
    _name = "delivery.price.rule.categ.price"
    _description = "Delivery Price Rules based on category"

    name = fields.Char()
    rule_id = fields.Many2one('delivery.price.rule', 'Rule', required=True, ondelete='cascade')
    categ_id = fields.Many2one('product.category', string='Product Category')
    discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    variable_factor = fields.Selection(
        [('weight', 'Weight'), ('volume', 'Volume'), ('wv', 'Weight * Volume'), ('price', 'Price'),
         ('quantity', 'Quantity')], 'Variable Factor', related='rule_id.variable_factor')
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0)
    list_price = fields.Float('Price', required=False, compute='_compute_discount_list_price', store=True)

    @api.depends('discount', 'price_unit')
    def _compute_discount_list_price(self):
        for line in self:
            price_reduce = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            line.list_price = price_reduce


