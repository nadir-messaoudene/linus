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

_logger = logging.getLogger(__name__)

def get_instance_id(model):
    ICPSudo = model.env['ir.config_parameter'].sudo()
    try:
        marketplace_instance_id = ICPSudo.get_param(
            'syncoria_base_marketplace.marketplace_instance_id')
        marketplace_instance_id = [int(s) for s in re.findall(
            r'\b\d+\b', marketplace_instance_id)]
    except:
        marketplace_instance_id = False

    if marketplace_instance_id:
        marketplace_instance_id = model.env['marketplace.instance'].sudo().search(
            [('id', '=', marketplace_instance_id[0])])
    return marketplace_instance_id



class FeedOrderFetchWizard(models.Model):
    _name = 'feed.orders.fetch.wizard'
    _description = 'Feed Orders Fetch Wizard'

    fetch_type = fields.Selection([
        ('to_odoo', 'Fetch Orders from Shopify'),
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


    def shopify_fetch_feed_orders(self, kwargs=None):
        _logger.info("shopify_fetch_feed_orders===>>>>{}".format(self))
        """Fetch Feed Orders"""
        OrderObj = self.env['shopify.feed.orders'].sudo()
        cr = self._cr
        marketplace_instance_id = self.instance_id or self._get_instance_id()
        version = marketplace_instance_id.marketplace_api_version or '2022-04'
        url = marketplace_instance_id.marketplace_host + \
            '/admin/api/%s/orders.json' % version

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
        if not self.date_from and not self.date_to:
            url += '?created_at_min=%s' % fields.Datetime.now().strftime(
                "%Y-%m-%dT00:00:00" + tz_offset)
            url += '&created_at_max=%s' % fields.Datetime.now().strftime(
                "%Y-%m-%dT23:59:59"  + tz_offset)

        _logger.info("url===>>>>{}".format(url))
        # Example: https://linus-sandbox.myshopify.com/admin/api/2022-01/orders.json?created_at_min=2022-04-05T00:00:00%2B0600&created_at_max=2022-04-05T23:59:59%2B0600


        # Request Parameters
        type_req = 'GET'
        headers = {'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password}
        order_list,next_link = self.env['marketplace.connector'].shopify_api_call(headers=headers,
                                                                        url=url,
                                                                        type=type_req)

        if url and order_list:
            _logger.info("\nurl >>>>>>>>>>>>>>>>>>>>>>" + str(url) +
                         "\nOrder #:--->" + str(len(order_list.get('orders'))))

        try:
            for sp_order in order_list['orders']:
                customer_name = sp_order.get('customer',{}).get('first_name','') + ' ' + sp_order.get('customer',{}).get('last_name','')
                order_id = OrderObj.create({
                    'name': self.env['ir.sequence'].sudo().next_by_code('shopify.feed.orders'),
                    'instance_id': marketplace_instance_id.id,
                    'shopify_id': sp_order['id'],
                    'order_data': json.dumps(sp_order),
                    'state': 'draft',
                    'shopify_webhook_call' : False,
                    'shopify_app_id' : sp_order.get('app_id'),
                    'shopify_confirmed' : sp_order.get('confirmed'),
                    'shopify_contact_email' : sp_order.get('contact_email'),
                    'shopify_currency' : sp_order.get('currency'),
                    'shopify_customer_name' : customer_name,
                    'shopify_customer_id' : sp_order.get('customer',{}).get('id',''),
                    'shopify_gateway' : sp_order.get('gateway'),
                    'shopify_order_number' : sp_order.get('order_number'),
                    'shopify_financial_status' : sp_order.get('financial_status'),
                    'shopify_fulfillment_status' : sp_order.get('fulfillment_status'),
                    'shopify_line_items' : len(sp_order.get('line_items')),
                    'shopify_user_id' : sp_order.get('user_id'),
                })
                order_id._cr.commit()
        except Exception as e:
            _logger.warning("Exception {}".format(e.args))
               
