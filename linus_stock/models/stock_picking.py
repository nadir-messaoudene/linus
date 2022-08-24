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

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_draft(self):
        self.state = 'draft'

    def do_unreserve(self, *args):
        if len(args) > 0 and args[0].get('active_model') == 'product.product' and args[0].get('active_id'):
            self.move_lines.filtered(lambda l: l.product_id.id == args[0].get('active_id'))._do_unreserve()
        else:
            self.move_lines._do_unreserve()
        self.package_level_ids.filtered(lambda p: not p.move_ids).unlink()