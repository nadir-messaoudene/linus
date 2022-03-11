# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, api, fields, tools, exceptions, _
import logging
logger = logging.getLogger(__name__)


class MarketplaceLogging(models.Model):
    _inherit = 'marketplace.logging'

    marketplace_type = fields.Selection(selection_add=[(
        'shopify', 'Shopify')], default='shopify', ondelete={'shopify': 'set default'})
    