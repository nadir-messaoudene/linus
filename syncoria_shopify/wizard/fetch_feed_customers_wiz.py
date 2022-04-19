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
        
        headers = {'X-Shopify-Access-Token':marketplace_instance_id.marketplace_api_password}
        type_req = 'GET'
        params = {"limit":250}
        
        summary = ''
        error = ''
        feed_customer_ids = self.env['shopify.feed.customers']
        items=[]
        while True:
            customer_list, next_link = self.env['marketplace.connector'].marketplace_api_call(
                headers=headers, 
                url=url, 
                type=type_req,
                marketplace_instance_id=marketplace_instance_id,
                params=params)
            if customer_list.get('customers'):
                items += customer_list['customers']
            if next_link:
                if next_link.get("next"):
                    url = next_link.get("next").get("url")
                else:
                    break
            else:
                break

        try:
            for customer in items:
                feed_customer_id, log_msg, error_msg = self.create_feed_customer(customer)
                feed_customer_ids += feed_customer_id
                summary += log_msg
                error += error_msg
            
            try:
                if feed_customer_ids and self.instance_id:
                    log_id = self.env['marketplace.logging'].sudo().create({
                        'name' : self.env['ir.sequence'].next_by_code('marketplace.logging'),
                        'create_uid' : self.env.user.id,
                        'marketplace_type' : self.instance_id.marketplace_instance_type,
                        'shopify_instance_id' : self.instance_id.id,
                        'level' : 'info',
                        'summary' : summary.replace('<br>','').replace('</br>','\n'),
                        'error' : error.replace('<br>','').replace('</br>','\n'),
                    })
                    log_id._cr.commit()
                    print("log_id ===>>>{}".format(log_id))
            except Exception as e:
                print("Exception-{}".format(e.args))


        except Exception as e:
            if customer_list.get('errors'):
                e = customer_list.get('errors')
            _logger.warning("Exception occured: %s", e)
            raise UserError(_("Error Occured: %s") % e)


        
    def create_feed_customer(self, customer_data):
        summary = ''
        error = ''
        feed_customer_id = False
        try:
            domain = [('shopify_id', '=', customer_data['id'])]
            feed_customer_id = self.env['shopify.feed.customers'].sudo().search(domain, limit=1)
            if feed_customer_id:
                feed_customer_id.write({
                    'customer_data': json.dumps(customer_data),
                    'customer_name': customer_data.get('first_name','') + ' ' + customer_data.get('last_name',''),
                    'email': customer_data.get('email'),     
                })
                message =  "Shopify Feed Customer Updated-{}, Customer ID-{}".format(feed_customer_id, customer_data['id'])
                summary += '\n' + message
                feed_customer_id.message_post(body=message)
                _logger.info(message)

            if not feed_customer_id:
                feed_customer_id = self.env['shopify.feed.customers'].sudo().create({
                    'name': self.env['ir.sequence'].next_by_code('shopify.feed.customers'),
                    'instance_id': self.instance_id.id,
                    'shopify_id': customer_data['id'],
                    'customer_data': json.dumps(customer_data),
                    'state': 'draft',
                    'customer_name': customer_data.get('first_name','') + ' ' + customer_data.get('last_name',''),
                    'email': customer_data.get('email', ''),
                })
                feed_customer_id._cr.commit()
                message =  "Shopify Feed Customer Created-{}, Customer ID-{}".format(feed_customer_id, customer_data['id'])
                summary += '\n' + message
                _logger.info(message)

        except Exception as e:
            message = str(e.args)
            summary += '\n' + message
            error += '\n' + message
            _logger.warning("Exception-{}".format(e.args))
        return feed_customer_id, summary, error