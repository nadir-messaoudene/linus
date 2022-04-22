# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                   #
###############################################################################


from odoo import models, fields


class InheritedStockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    marketplace_type = fields.Selection([], string="Marketplace Type")
    shopify_instance_id = fields.Many2one("marketplace.instance", string="Shopify Instance ID")