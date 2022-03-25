# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import json
import re
import logging
_logger = logging.getLogger(__name__)


class FeedOrderFetchWizard(models.Model):
    _name = 'feed.customers.fetch.wizard'
    _description = 'Feed Customers Fetch Wizard'

    fetch_type = fields.Selection([
        ('to_odoo', 'Fetch Customers from Shopify'),
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

    def shopify_fetch_feed_customers_to_odoo(self):
        PartnerObj = self.env['shopify.feed.customers']
        marketplace_instance_id = self.instance_id or self._get_instance_id()
        type_req = 'GET'
        version = marketplace_instance_id.marketplace_api_version or '2022-01'
        url = marketplace_instance_id.marketplace_host +  '/admin/api/%s/customers.json'%version
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
        
        
        headers = {'X-Shopify-Access-Token':marketplace_instance_id.marketplace_api_password}
        type_req = 'GET'
        customer_list = self.env['marketplace.connector'].marketplace_api_call(headers=headers, url=url, type=type_req,marketplace_instance_id=marketplace_instance_id)
        try:
            for customer in customer_list['customers']:
                self.create_feed_customer(customer)

        except Exception as e:
            if customer_list.get('errors'):
                e = customer_list.get('errors')
            _logger.warning("Exception occured: %s", e)
            raise UserError(_("Error Occured: %s") % e)


        
    def create_feed_customer(self, customer_data):
        feed_customer_id = False
        try:
            domain = [('shopify_id', '=', customer_data['id'])]
            feed_customer_id = self.env['shopify.feed.customers'].sudo().search(domain, limit=1)
            if not feed_customer_id:
                feed_customer_id = self.env['shopify.feed.customers'].sudo().create({
                    'name': self.env['ir.sequence'].next_by_code('shopify.feed.customers'),
                    'instance_id': self.instance_id.id,
                    'shopify_id': customer_data['id'],
                    'customer_data': json.dumps(customer_data),
                    'state': 'draft'
                })
                feed_customer_id._cr.commit()
                _logger.info(
                    "Shopify Feed customer Created-{}".format(feed_customer_id))
        except Exception as e:
            _logger.warning("Exception-{}".format(e.args))
        return feed_customer_id