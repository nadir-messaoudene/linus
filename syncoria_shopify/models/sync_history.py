# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class GsSyncHistory(models.Model):
    """Synchronisation History for Quickbase and Odoo"""
    _inherit = 'marketplace.sync.history'
   
    marketplace_type = fields.Selection(
        selection_add=[('shopify', 'Shopify')],
        # readonly=True 
    )

    def set_sync_history(self):
        sync = self.env['marketplace.sync.history'].sudo().search([('marketplace_type', '=', 'shopify')])
        if not sync:
            self.env['marketplace.sync.history'].sudo().create({
                'name':'Shopify Sync History'
            })

