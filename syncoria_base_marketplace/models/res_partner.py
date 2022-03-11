# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    marketplace = fields.Boolean(
        string='Marketplace',
    )
    marketplace_type = fields.Selection(
        selection=[], 
        string="Marketplace Type",
        
    )

        


    



