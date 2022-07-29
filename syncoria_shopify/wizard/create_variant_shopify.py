# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################
import json
import logging
import datetime
from odoo import fields, models, exceptions, _
from odoo.http import request
import re
import pprint
import time

from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class CreateVariantShopifyWizard(models.Model):
    _name = 'create.variant.shopify'

    shopify_instance_ids = fields.Many2many('marketplace.instance', string="Shopify Store")
    product_id = fields.Many2one('product.product', 'Product')

    def action_create(self):
        if self.product_id and self.shopify_instance_ids:
            for instance_obj in self.shopify_instance_ids:
                # print(instance_obj)
                self.product_id.action_create_shopify_product(instance_obj)
        return