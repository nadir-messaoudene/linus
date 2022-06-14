# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import json
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
        log_msg = ''
        instance_id = self.instance_id or self._get_instance_id()
        version = instance_id.marketplace_api_version or '2022-01'
        url = instance_id.marketplace_host + \
            '/admin/api/%s/products.json' % version

        tz_offset = '-00:00'
        if self.env.user and self.env.user.tz_offset:
            tz_offset = self.env.user.tz_offset

        if self.date_from and not self.date_to:
            url += '?created_at_min=%s' % self.date_from.strftime(
                "%Y-%m-%dT00:00:00" + tz_offset)
        if not self.date_from and self.date_to:
            url += '?created_at_max=%s' % self.date_to.strftime(
                "%Y-%m-%dT23:59:59" + tz_offset)
        if self.date_from and self.date_to:
            url += '?created_at_min=%s' % self.date_from.strftime(
                "%Y-%m-%dT00:00:00" + tz_offset)
            url += '&created_at_max=%s' % self.date_to.strftime(
                "%Y-%m-%dT23:59:59" + tz_offset)


        headers = {
            'X-Shopify-Access-Token': instance_id.marketplace_api_password}
        type_req = 'GET'
        params = {"limit": 250}
        products = []
        while True:
            fetched_products,next_link = self.env[
                'marketplace.connector'].shopify_api_call(
                headers=headers,
                url=url,
                type=type_req,
                marketplace_instance_id=instance_id,
                params=params
            )
            try:
                products += fetched_products['products']
                if next_link:
                    if next_link.get("next"):
                        url = next_link.get("next").get("url")

                    else:
                        break
                else:
                    break
            except Exception as e:
                _logger.info("Exception occured: %s", e)
                raise exceptions.UserError(_("Error Occured %s") % e)
        configurable_products = {"products": products}
        _logger.info("Number of Products: {}".format(len(configurable_products.get('products'))))

        feed_products = self.env['shopify.feed.products']
        child_products = self.env['shopify.feed.products']
        if configurable_products.get('products'):
            for product in configurable_products.get('products'):
                feed_product = self.create_feed_parent_product(product)
                feed_products += feed_product

                for variant in product.get('variants'):
                    child_product = self.create_feed_variant_product(variant, feed_product)
                    child_products += child_product

        # message = "Parent Product Created: {}".format(len(feed_products))
        # log_msg += message
        # message = "Child Product Created: {}".format(len(child_products))
        _logger.info("Parent Product Created: {}".format(len(feed_products)))
        _logger.info("Child Product Created: {}".format(len(child_products)))

                


    def create_feed_parent_product(self, product):
        shopify_feed_product = self.env['shopify.feed.products']
        domain = [("shopify_id","=",product['id'])]
        feed_product = shopify_feed_product.search(domain,limit=1)
        try:
            feed_product_vals = {
                    'instance_id': self.instance_id.id,
                    'parent': True,
                    'title': product['title'],
                    'shopify_id': product['id'],
                    'inventory_id': product.get('inventory_item_id'),
                    'product_data': json.dumps(product),
                }
                
            if not feed_product:
                record = shopify_feed_product.sudo().create(feed_product_vals)
                _logger.info("Shopify Feed Parent Product Created-{}".format(record))
                self._cr.commit()
            else:
                record = feed_product.write(feed_product_vals)
                _logger.info("Shopify Feed already exists-{}".format(record))


        except Exception as e:
            _logger.warning("Exception-{}".format(e.args))
        return feed_product
    
    
    def create_feed_variant_product(self, product, parent_id):
        shopify_feed_product = self.env['shopify.feed.products']
        existing_product = self.env['shopify.feed.products']
        try:
            existing_product = shopify_feed_product.search([("shopify_id", "=", product['id'])], limit=1)
            child_product_vals = {
                'instance_id': self.instance_id.id,
                'parent': False,
                'title': product['title'],
                'shopify_id': product['id'],
                'inventory_id': product.get('inventory_item_id'),
                'product_data': str(product),
                'product_wiz_id' : self.id,
                'barcode': product.get('barcode'),
                'default_code': product.get('sku'),
                'parent_id': parent_id.id,
                'parent_title': parent_id.title,
            }

            if not existing_product:
                existing_product = self.env['shopify.feed.products'].sudo().create(child_product_vals)
                _logger.info("Shopify Feed Varaint Product Created-{}".format(existing_product))
                existing_product._cr.commit()
            else:
                existing_product.write(child_product_vals)
                _logger.info("Shopify Feed already exists-{}".format(existing_product))

        except Exception as e:
            _logger.warning("Exception-{}".format(e.args))
        return existing_product


