# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, api, fields, tools, exceptions, _
import logging
logger = logging.getLogger(__name__)


class MarketplaceLogging(models.Model):
    _name = 'marketplace.logging'
    _description = """Channel Advisor Logging"""
    _order = 'id DESC'

    name = fields.Char(
        string='Name',
    )
    create_uid = fields.Integer(string='Created by', required=True)
    marketplace_type = fields.Selection(
        selection=[], default='channel_advisor', required=True)
    shopify_instance_id = fields.Many2one("marketplace.instance", string="Shopify Instance ID")
    level = fields.Char(string='Level', required=True)
    summary = fields.Text(string='Summary', required=True)
    error = fields.Text(string='Error')
    type = fields.Selection(
        string='Type',
        selection=[('client', 'Client'), ('server', 'Server')]
    )
    model_name = fields.Char(
        string='Model Name',
    )
