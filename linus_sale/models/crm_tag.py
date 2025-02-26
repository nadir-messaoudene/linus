# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import randint

from odoo import fields, models
from odoo.exceptions import UserError
import logging

logger = logging.getLogger(__name__)
class Tag(models.Model):
    _inherit = "crm.tag"

    is_depend = fields.Boolean('Is Depend', default=False)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        order_types = self.env['crm.tag'].search([('x_studio_is_order_type','=',True)])
        for tag in self.tag_ids:
            logger.info(tag.name)
        flag = False
        order_type_independent = self.tag_ids.filtered(lambda l: l.x_studio_is_order_type == True and l.is_depend == False)
        if len(order_type_independent) > 1:
            flag = True
        order_type_dependent = self.tag_ids.filtered(lambda l: l.x_studio_is_order_type == True and l.is_depend == True)
        logger.info(self.tag_ids)
        logger.info(order_type_dependent)
        logger.info(order_type_independent)
        if 1 < len(self.tag_ids) == len(order_type_dependent):
            flag = True
        if flag:
            raise UserError('Please check your Order Type.')
        return super().action_confirm()