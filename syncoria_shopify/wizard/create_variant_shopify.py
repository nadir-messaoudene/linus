# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################
import json
import logging
import datetime
from odoo import fields, models, exceptions, _, api
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
    product_tpml_id = fields.Many2one('product.template', 'Product Template')
    note = fields.Char(compute='compute_note')

    def action_create(self):
        if self.product_id and self.shopify_instance_ids:
            shopify_instance_already_created_list = self.get_product_shopify_instances(self.product_id)
            for instance_obj in self.shopify_instance_ids:
                if instance_obj.id not in shopify_instance_already_created_list:
                    self.product_id.action_create_shopify_product(instance_obj)

        if self.product_tpml_id and self.shopify_instance_ids:
            shopify_instance_already_created_list = self.get_product_template_shopify_instances(self.product_tpml_id)
            for instance_obj in self.shopify_instance_ids:
                if instance_obj.id not in shopify_instance_already_created_list:
                    self.product_tpml_id.action_create_shopify_product(instance_obj)
        return

    @api.depends('product_id', 'product_tpml_id')
    def compute_note(self):
        result = ''
        # Product Product
        if self.product_id:
            if self.product_id.shopify_instance_id:
                result += self.product_id.shopify_instance_id.name
            shopify_multi_store_obj = self.env['shopify.multi.store'].search([('product_id', '=', self.product_id.id)])
            if len(shopify_multi_store_obj) > 0:
                if len(result) > 0:
                    result += ', '
                l_tmp = []
                for i in shopify_multi_store_obj:
                    l_tmp.append(i.shopify_instance_id.name)
                result += ', '.join(l_tmp)
        # Product Template
        if self.product_tpml_id:
            if self.product_tpml_id.shopify_instance_id:
                result += self.product_tpml_id.shopify_instance_id.name
            shopify_multi_store_obj = self.env['shopify.multi.store'].search(
                [('product_tmpl_id', '=', self.product_tpml_id.id)])
            if len(shopify_multi_store_obj) > 0:
                if len(result) > 0:
                    result += ', '
                l_tmp = []
                for i in shopify_multi_store_obj:
                    if i.shopify_instance_id.name not in l_tmp:
                        l_tmp.append(i.shopify_instance_id.name)
                result += ', '.join(l_tmp)

        if len(result) > 0:
            self.note = 'Please notice that Product: %s already been created on Store(s): %s. Do not select these Store(s) on the list above.' % (
            self.product_id.display_name or self.product_tpml_id.name, result)
        else:
            self.note = ''

    def get_product_shopify_instances(self, product_obj):
        result = []
        if product_obj.shopify_instance_id:
            result.append(product_obj.shopify_instance_id.id)
        shopify_multi_store_obj = self.env['shopify.multi.store'].search([('product_id', '=', product_obj.id)])
        if len(shopify_multi_store_obj) > 0:
            for store in shopify_multi_store_obj:
                result.append(store.shopify_instance_id.id)
        return result

    def get_product_template_shopify_instances(self, product_template_obj):
        result = []
        if product_template_obj.shopify_instance_id:
            result.append(product_template_obj.shopify_instance_id.id)
        shopify_multi_store_obj = self.env['shopify.multi.store'].search(
            [('product_tmpl_id', '=', product_template_obj.id)])
        if len(shopify_multi_store_obj) > 0:
            for store in shopify_multi_store_obj:
                result.append(store.shopify_instance_id.id)
        return result
