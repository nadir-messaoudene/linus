# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                   #
###############################################################################


from odoo import models, fields


class InheritedSaleOrder(models.Model):
    _inherit = "sale.order"

    marketplace_type = fields.Selection([], string="Marketplace Type")
    shopify_instance_id = fields.Many2one("marketplace.instance", string="Shopify Instance ID")