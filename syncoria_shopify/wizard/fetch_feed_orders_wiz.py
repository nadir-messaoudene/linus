# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

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


    def shopify_fetch_feed_orders(self, kwargs=None):
        """Fetch Feed Orders"""
        OrderObj = self.env['shopify.feed.orders'].sudo()
        cr = self._cr
        marketplace_instance_id = self.instance_id or self._get_instance_id()
        version = marketplace_instance_id.marketplace_api_version or '2022-04'
        url = marketplace_instance_id.marketplace_host + \
            '/admin/api/%s/orders.json' % version

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

        # Request Parameters
        type_req = 'GET'
        headers = {'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password}
        order_list = self.env['marketplace.connector'].shopify_api_call(headers=headers,
                                                                        url=url,
                                                                        type=type_req)

        if url and order_list:
            _logger.info("\nurl >>>>>>>>>>>>>>>>>>>>>>" + str(url) +
                         "\nOrder #:--->" + str(len(order_list.get('orders'))))

        try:
            for sp_order in order_list['orders']:
                OrderObj.create({
                    'instance_id': self.instance_id.id,
                    'shopify_id': sp_order['id'],
                    'order_data': str(sp_order),
                })
        except Exception as e:
            _logger.warning("Exception {}".format(e.args))
               