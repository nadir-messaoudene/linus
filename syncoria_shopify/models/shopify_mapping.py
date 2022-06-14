from odoo import fields, models, api


class ShopifyMapProduct(models.Model):
    _name = 'shopify.map.product'
    _description = 'Shopify Product Mapping'

    name = fields.Char()
