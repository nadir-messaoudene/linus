# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import requests
import logging
import base64
import re
from odoo import models, fields, exceptions, _
from odoo.http import request
from pprint import pprint

_logger = logging.getLogger(__name__)


class FeedProductsFetchWizard(models.Model):
    _name = 'feed.products.fetch.wizard'
    _description = 'Feed Products Fetch Wizard'

    fetch_type = fields.Selection([
        ('to_odoo', 'Fetch Products from Shopify'),
    ], default='to_odoo', string="Operation Type")

    instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
    )
    date_from = fields.Date('From')
    date_to = fields.Date('To')


    def _get_instance_id(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        try:
            marketplace_instance_id = ICPSudo.get_param(
                'syncoria_base_marketplace.marketplace_instance_id')
            marketplace_instance_id = [int(s) for s in re.findall(
                r'\b\d+\b', marketplace_instance_id)]
        except:
            marketplace_instance_id = False

        if marketplace_instance_id:
            marketplace_instance_id = self.env['marketplace.instance'].sudo().search(
                [('id', '=', marketplace_instance_id[0])])
        return marketplace_instance_id


    def shopify_fetch_feed_products_to_odoo(self):
        instance_id = self.instance_id or self._get_instance_id()
        version = instance_id.marketplace_api_version or '2022-01'
        url = instance_id.marketplace_host + \
            '/admin/api/%s/products.json' % version
        if self.date_from and not self.date_to:
            url += '?created_at_min=%s' % self.date_from.strftime(
                "%Y-%m-%dT00:00:00-04:00")
        if not self.date_from and self.date_to:
            url += '?created_at_max=%s' % self.date_to.strftime(
                "%Y-%m-%dT00:00:00-04:00")
        if self.date_from and self.date_to:
            url += '?created_at_min=%s' % self.date_from.strftime(
                "%Y-%m-%dT00:00:00-04:00")
            url += '&created_at_max=%s' % self.date_to.strftime(
                "%Y-%m-%dT00:00:00-04:00")


        headers = {
            'X-Shopify-Access-Token': instance_id.marketplace_api_password}
        type_req = 'GET'

        configurable_products = self.env[
            'marketplace.connector'].shopify_api_call(
            headers=headers,
            url=url,
            type=type_req,
            marketplace_instance_id=instance_id
        )

        if configurable_products.get('products'):
            for product in configurable_products.get('products'):
                try:
                    self.create_parent_product(product)
                    if product.get('variants'):
                        # if len(product.get('variants')) == 1:
                        #     """Simple Product"""
                        # if len(product.get('variants')) > 1:
                        #     """Complex Product"""
                        if len(product.get('variants')) > 0:
                            for var in product.get('variants'):
                                self.create_variant_product(var)
                except Exception as e:
                    _logger.warning("Exception-{}".format(e.args))

    def create_parent_product(self, product):
        try:
            record = self.env['shopify.feed.products'].sudo().create({
                'instance_id': self.instance_id.id,
                'parent': True,
                'title': product['title'],
                'shopify_id': product['id'],
                'inventory_id': product.get('inventory_item_id'),
                'product_data': str(product),
            })
            record._cr.commit()
        except Exception as e:
            _logger.warning("Exception-{}".format(e.args))

    def create_variant_product(self, product):
        try:
            variant = self.env['shopify.feed.products'].sudo().create({
                'instance_id': self.instance_id.id,
                'parent': False,
                'title': product['title'],
                'shopify_id': product['id'],
                'inventory_id': product.get('inventory_item_id'),
                'product_data': str(product),
            })
            variant._cr.commit()
        except Exception as e:
            _logger.warning("Exception-{}".format(e.args))