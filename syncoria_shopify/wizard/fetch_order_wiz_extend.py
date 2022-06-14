# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import json
import logging
from odoo import fields, models, exceptions, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class OrderFetchWizardExtend(models.Model):
    _inherit = 'order.fetch.wizard'

    def compute_price_unit(self, product_id, price_unit):
        item_price = price_unit
        marketplace_instance_id = self._get_instance_id()
        pricelist_id = marketplace_instance_id.pricelist_id
        pricelist_price = marketplace_instance_id.compute_pricelist_price
        if pricelist_price and pricelist_id and 'product.product' in str(product_id):
            item_line = marketplace_instance_id.pricelist_id.item_ids.filtered(
                lambda l: l.product_tmpl_id.id == product_id.product_tmpl_id.id)
            if not item_line:
                _logger.warning("No Item Line found for {}".format(product_id))
            item_price = item_line.fixed_price if item_line else item_price
        if pricelist_price and pricelist_id and 'product.template' in str(product_id):
            item_line = marketplace_instance_id.pricelist_id.item_ids.filtered(
                lambda l: l.product_tmpl_id.id == product_id.id)
            if not item_line:
                _logger.warning("No Item Line found for {}".format(product_id))
            item_price = item_line.fixed_price if item_line else item_price
        return item_price

    def create_feed_orders(self, order_data):
        log_msg = ''
        error_msg = ''
        feed_order_id = False
        try:
            marketplace_instance_id = self.instance_id or self._get_instance_id()
            if order_data.get('customer', {}).get('first_name', '') is None:
                customer_name = 'No name provided'
            else:
                customer_name = order_data.get('customer',{}).get('first_name','') + ' ' + order_data.get('customer',{}).get('last_name','')
            domain = [('shopify_id', '=', order_data['id'])]
            domain += [('instance_id', '=', marketplace_instance_id.id)]
            feed_order_id = self.env['shopify.feed.orders'].sudo().search(domain, limit=1)
            if not feed_order_id:
                feed_order_id = self.env['shopify.feed.orders'].sudo().create({
                    'name': self.env['ir.sequence'].sudo().next_by_code('shopify.feed.orders'),
                    'instance_id': marketplace_instance_id.id,
                    'shopify_id': order_data['id'],
                    'order_data': json.dumps(order_data),
                    'state': 'draft',
                    'shopify_webhook_call' : False,
                    'shopify_app_id' : order_data.get('app_id'),
                    'shopify_confirmed' : order_data.get('confirmed'),
                    'shopify_contact_email' : order_data.get('contact_email'),
                    'shopify_currency' : order_data.get('currency'),
                    'shopify_customer_name' : customer_name,
                    'shopify_customer_id' : order_data.get('customer',{}).get('id',''),
                    'shopify_gateway' : order_data.get('gateway'),
                    'shopify_order_number' : order_data.get('order_number'),
                    'shopify_financial_status' : order_data.get('financial_status'),
                    'shopify_fulfillment_status' : order_data.get('fulfillment_status'),
                    'shopify_line_items' : len(order_data.get('line_items')),
                    'shopify_user_id' : order_data.get('user_id'),
                })
                
                msg = _("Shopify Feed Order Created-{}".format(feed_order_id))
                _logger.info(msg)
                log_msg += "<br>" + msg + "</br>"
            else:
                feed_order_id.write({
                    'order_data': json.dumps(order_data),
                    'shopify_app_id' : order_data.get('app_id'),
                    'shopify_confirmed' : order_data.get('confirmed'),
                    'shopify_contact_email' : order_data.get('contact_email'),
                    'shopify_currency' : order_data.get('currency'),
                    'shopify_customer_name' : customer_name,
                    'shopify_customer_id' : order_data.get('customer',{}).get('id',''),
                    'shopify_gateway' : order_data.get('gateway'),
                    'shopify_order_number' : order_data.get('order_number'),
                    'shopify_financial_status' : order_data.get('financial_status'),
                    'shopify_fulfillment_status' : order_data.get('fulfillment_status'),
                    'shopify_line_items' : len(order_data.get('line_items')),
                    'shopify_user_id' : order_data.get('user_id'),
                })
    
                msg = _("\nShopify Feed Order Updated-{}".format(feed_order_id))
                _logger.info(msg)
                log_msg += "<br>" + msg + "</br>"

            feed_order_id._cr.commit()
        except Exception as e:
            error_msg += '<br> Shopify Order Feed Order Creation: {} Exception-{} </br>'.format(order_data.get('order_number'), e.args)
        return feed_order_id, log_msg, error_msg