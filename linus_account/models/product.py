# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import operator as py_operator
from ast import literal_eval
from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import float_is_zero
from odoo.tools.float_utils import float_round

class ProductTemplate(models.Model):
    _inherit = "product.template"

    country_of_origin_ids = fields.Many2many('res.country', 'product_template_res_country_rel', 'product_template_id', 'country_id', string='Country of Origin')