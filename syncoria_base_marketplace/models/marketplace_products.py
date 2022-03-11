# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, api, fields, tools, exceptions, _
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    marketplace_type = fields.Selection([], string="Marketplace Type")

class ProductProduct(models.Model):
    _inherit = 'product.product'

    marketplace_type = fields.Selection([], string="Marketplace Type")

class ProductCateg(models.Model):
    _inherit = 'product.category'

    marketplace_type = fields.Selection([], string="Marketplace Type")

# class ProductImaget(models.Model):
#     _inherit = 'product.image'
    
#     marketplace_type = fields.Selection([], string="Marketplace Type")

class ProductAttributeExtended(models.Model):
    _inherit = 'product.attribute'

    marketplace_type = fields.Selection([], string="Marketplace Type")

class ProductAttributeValueExtended(models.Model):
    _inherit = 'product.attribute.value'

    marketplace_type = fields.Selection([], string="Marketplace Type")

class PTAL(models.Model):
    _inherit = 'product.template.attribute.line'

    marketplace_type = fields.Selection([], string="Marketplace Type")

class SCPQ(models.TransientModel):
    _inherit = 'stock.change.product.qty'

    marketplace_type = fields.Selection([], string="Marketplace Type")