# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import logging
import datetime
from odoo import fields, models, exceptions, _
from pprint import pprint
import re
logger = logging.getLogger(__name__)


class OrderFetchWizard(models.Model):
    _name = 'order.fetch.wizard'
    _description = 'Order Fetch Wizard'

    
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
            marketplace_instance_id = ICPSudo.get_param('syncoria_base_marketplace.marketplace_instance_id')
            marketplace_instance_id = [int(s) for s in re.findall(r'\b\d+\b', marketplace_instance_id)]
        except:
            marketplace_instance_id = False
        
        if marketplace_instance_id:
            marketplace_instance_id = self.env['marketplace.instance'].sudo().search([('id','=',marketplace_instance_id[0])])
        return marketplace_instance_id
           

    def find_customer_id(self, item, ids, partner_vals, main=False):
        marketplace_instance_id = self._get_instance_id()
        if marketplace_instance_id:
            kwargs = {'marketplace_instance_id':marketplace_instance_id}
            if hasattr(self, '%s_fetch_orders' % marketplace_instance_id.marketplace_instance_type):
                return getattr(self, '%s_fetch_orders' % marketplace_instance_id.marketplace_instance_type)(kwargs)
        else:
            logger.warning(_("No Marketplace Instance Setup!"))

    def fetch_query(self, vals):
        """constructing the query, from the provided column names"""
        query_str = ""
        if not vals:
            return
        for col in vals:
            query_str += " " + str(col) + ","
        return query_str[:-1]

    def fetch_orders(self):
        marketplace_instance_id = self._get_instance_id()
        if marketplace_instance_id:
            kwargs = {'marketplace_instance_id': marketplace_instance_id}
            if hasattr(self, '%s_fetch_orders' % marketplace_instance_id.marketplace_instance_type):
                return getattr(self, '%s_fetch_orders' % marketplace_instance_id.marketplace_instance_type)(kwargs)
        else:
            logger.warning(_("No Marketplace Instance Setup!"))


    def fetch_taxes(self):
        marketplace_instance_id = self._get_instance_id()
        if marketplace_instance_id:
            # marketplace_instance_id = self.env['marketplace.instance'].sudo().search([('id','=',marketplace_instance_id[0])])
            kwargs = {'marketplace_instance_id': marketplace_instance_id}
            if hasattr(self, '%s_fetch_taxes' % marketplace_instance_id.marketplace_instance_type):
                return getattr(self, '%s_fetch_taxes' % marketplace_instance_id.marketplace_instance_type)(kwargs)
        else:
            logger.warning(_("No Marketplace Instance Setup!"))

    def _get_shipping(self, item_val):
        for parts in item_val['extension_attributes']['shipping_assignments']:
            for key1,value1 in parts.items():
                if key1 == 'shipping':
                    for key2,value2 in value1.items():
                        value_type = type(value2)
                        if value_type == dict:
                            for key3,value3 in value2.items():
                                if  key3 == 'address_type':
                                    shipping = value2
        return shipping


    def push_tracking(self):
        marketplace_instance_id = self._get_instance_id()
        if marketplace_instance_id:
            kwargs = {'marketplace_instance_id': marketplace_instance_id}
            if hasattr(self, '%s_push_tracking' % marketplace_instance_id.marketplace_instance_type):
                return getattr(self, '%s_push_tracking' % marketplace_instance_id.marketplace_instance_type)(kwargs)
        else:
            logger.warning(_("No Marketplace Instance Setup!"))
