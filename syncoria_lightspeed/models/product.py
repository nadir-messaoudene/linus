import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class ProductProductInherit(models.Model):
    _inherit = "product.product"

    lightspeed_item_id = fields.Char(string='Lightspeed Item ID')
    lightspeed_system_sku = fields.Char(string='System ID')
    lightspeed_taxable = fields.Boolean(string='Lightspeed Taxable')
    lightspeed_discountable = fields.Boolean(string='Lightspeed Discountable')
    lightspeed_upc = fields.Char(string='UPC')
    lightspeed_manufacturer_sku = fields.Char(string='Manufact.SKU')
    lightspeed_publish_to_ecom = fields.Boolean(string='Publish To Ecom')
    lightspeed_category_id = fields.Integer(string='Category ID')
    lightspeed_tax_class_id = fields.Integer(string='Lightspeed Tax Class ID')

