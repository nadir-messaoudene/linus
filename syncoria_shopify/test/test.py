# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _

import pprint
import json
import logging
_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    
    @api.model
    def create(self, values):
        print('Product.product:create===>>>' +str(values))
        result = super(ProductProduct, self).create(values)
        return result

    
    def write(self, values):
        print('Product.product:write===>>>' +str(values))
        result = super(ProductProduct, self).write(values)
        return result
    

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    
    @api.model
    def create(self, values):
        print('Product.template:create===>>>' +str(values))
        result = super(ProductTemplate, self).create(values)
        return result
    
    def write(self, values):
        print('Product.template:write===>>>' +str(values))
        result = super(ProductTemplate, self).write(values)
        return result

class ProductTemplateAttLine(models.Model):
    _inherit = 'product.template.attribute.line'

    
    @api.model
    def create(self, values):
        print('product.template.attribute.line:create===>>>' +str(values))
        result = super(ProductTemplateAttLine, self).create(values)
        return result
    
    def write(self, values):
        print('product.template.attribute.line:write===>>>' +str(values))
        result = super(ProductTemplateAttLine, self).write(values)
        return result


class ProductTemplateAttributeValue(models.Model):
    _inherit = 'product.template.attribute.value'

    
    @api.model
    def create(self, values):
        print('product.template.attribute.value:create===>>>' +str(values))
        result = super(ProductTemplateAttributeValue, self).create(values)
        return result
    
    def write(self, values):
        print('product.template.attribute.value:write===>>>' +str(values))
        result = super(ProductTemplateAttributeValue, self).write(values)
        return result