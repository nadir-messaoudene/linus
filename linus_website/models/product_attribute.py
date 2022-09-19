import logging
from collections import defaultdict
from functools import reduce

from odoo import models, fields, api
from odoo.tools import populate
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)


class ProductAttributeInherit(models.Model):
    _inherit = "product.attribute"

    def get_published_values(self):
        values = self.env['product.attribute.value']
        product_tmpl_ids = self.product_tmpl_ids.filtered(lambda p: p.is_published)
        for product_template in self.product_tmpl_ids.filtered(lambda p: p.is_published):
            attribute_values = product_template.attribute_line_ids.filtered(lambda l: l.attribute_id == self).value_ids
            valid_attribute_values = attribute_values.filtered(lambda l: l not in product_template.exclude_product_template_value_ids)
            for val in valid_attribute_values:
                if val not in values:
                    values += val
        return values


class ProductTemplateAttributeValueInherit(models.Model):
    _inherit = "product.template.attribute.value"

    def _only_active(self):
        if self.env.context.get('website_id'):
            product_template = self.mapped('product_tmpl_id')
            return self.filtered(lambda ptav: ptav.product_attribute_value_id not in product_template.exclude_product_template_value_ids)
        return self.filtered(lambda ptav: ptav.ptav_active)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    attribute_val_ids = fields.Many2many('product.attribute.value', compute='_compute_attribute_value_ids', string='Attribute Values')
    exclude_product_template_value_ids = fields.Many2many('product.attribute.value', string="Exclude Attribute Values",
                                                          domain="[('id', 'in', attribute_val_ids)]")

    @api.depends('attribute_line_ids')
    def _compute_attribute_value_ids(self):
        for record in self:
            record.attribute_val_ids = record.attribute_line_ids.value_ids

    @api.onchange('exclude_product_template_value_ids')
    def _check_at_least_possible_attribute_value(self):
        for record in self:
            for attribute_line in record.attribute_line_ids:
                exclude_attribute_values = record.exclude_product_template_value_ids.filtered(lambda l: l in attribute_line.value_ids)
                if len(exclude_attribute_values) == attribute_line.value_count:
                    raise ValidationError('You cannot exclude all values of an attribute. Must exist at least one possible combination')

    def _search_get_detail(self, website, order, options):
        res = super(ProductTemplate, self)._search_get_detail(website, order, options)
        if res.get('base_domain'):
            res['base_domain'].append([('is_published', '=', True)])
            attrib_values = options.get('attrib_values')
            if attrib_values:
                attrib = None
                ids = []
                for value in attrib_values:
                    if not attrib:
                        attrib = value[0]
                        ids.append(value[1])
                    elif value[0] == attrib:
                        ids.append(value[1])
                    else:
                        res['base_domain'].append([('exclude_product_template_value_ids', 'not in', ids)])
                        attrib = value[0]
                        ids = [value[1]]
                if attrib:
                    res['base_domain'].append([('exclude_product_template_value_ids', 'not in', ids)])
        return res



