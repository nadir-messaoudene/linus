# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import pprint
import re

from odoo.exceptions import AccessError, UserError
from ..shopify.utils import *
from odoo import models, api, fields, tools, exceptions, _
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    shopify_id = fields.Char(string="Shopify Id", store=True, copy=False)
    shopify_inventory_id = fields.Char(
        string="Shopify Inventory Id", store=True, copy=False)
    marketplace_type = fields.Selection(selection_add=[('shopify', 'Shopify')])
    shopify_categ_ids = fields.One2many('shopify.product.category',
                                        'product_tmpl_id',
                                        string="Shopify Categories",
                                        readonly=True)
    shopify_type = fields.Char(string="Shopify Product Type",
                               readonly=True, store=True)
    custom_option = fields.Boolean(string="Custom Option", default=False)
    # New Fields
    shopify_published_scope = fields.Char()
    shopify_tags = fields.Char()
    shopify_template_suffix = fields.Char()
    shopify_variants = fields.Char()
    shopify_vendor = fields.Char()
    # Fields for Shopify Products
    shopify_compare_price = fields.Monetary(string='Compare at price')
    shopify_charge_tax = fields.Boolean(string='Charge tax?')
    shopify_track_qty = fields.Boolean(string='Track quantity?')
    shopify_product_status = fields.Selection(
        string='Product status',
        selection=[('draft', 'Draft'), ('active', 'Active'),
                   ('archived', 'Archived')],
        default='active',
    )
    shopify_collections = fields.Char()
    shopify_origin_country_id = fields.Many2one(
        string='Shopify Country Code of Origin',
        comodel_name='res.country',
        ondelete='restrict',
    )
    shopify_province_origin_id = fields.Many2one(
        string='Shopify Province Code of Origin',
        comodel_name='res.country.state',
        ondelete='restrict',
    )
    #Currency Conversion
    shopify_currency_id = fields.Many2one(
        string='Shopify Currency',
        comodel_name='res.currency',
        ondelete='restrict',
    )
    shopify_price = fields.Float(
        string='Shopify Product Price',
    )
    
    def computer_shopify_price(self):
        for rec in self:
            rec.shopify_price = rec.list_price
            if rec.shopify_currency_id:
                if rec.shopify_currency_id != rec.currency_id:
                    rec.shopify_price = rec.list_price*rec.shopify_currency_id.rate


    def action_create_shopify_product(self):
        data = get_protmpl_vals(self, {})
        _logger.info("data ===>>>", data)
        shopify_pt_request(self, data, 'create')

    def shopify_create_product(self, result, values):
        if not values.get('shopify_id') and result.marketplace_type == 'shopify':
            data = get_protmpl_vals(result, values)
            shopify_pt_request(self, data, 'create')

    def action_update_shopify_product(self):
        data = get_protmpl_vals(self, {"req_type": 'update'})
        res = shopify_pt_request(self, data, 'update')

    def server_action_shopify_create_update_product(self):
        for record in self:
            if record.marketplace_type == 'shopify':
                if record.shopify_id:
                    record.action_update_shopify_product()
                else:
                    record.action_create_shopify_product()
            else:
                raise UserError(
                    _("Marketplace type is not set for Shopify(Product: %s)") % record.name)

    # @api.model
    # def create(self, values):
    #     print(values)
    #     if values.get('shopify_id'):
    #         ProTmpl = self.env['product.template'].sudo()
    #         product = ProTmpl.search(
    #             [('shopify_id', '=', values.get('shopify_id'))], limit=1)
    #         if product:
    #             _logger.warning(
    #                 "Product already exists with id=%s and shopify id = %s", product.id, product.shopify_id)
    #             return product.id
    #         else:
    #             result = super(ProductTemplate, self).create(values)
    #     else:
    #         result = super(ProductTemplate, self).create(values)

    #     self.shopify_create_product(result, values)
    #     return result


class ProductProductShopify(models.Model):
    _inherit = 'product.product'

    marketplace_type = fields.Selection(selection_add=[('shopify', 'Shopify')])
    shopify_categ_ids = fields.One2many('shopify.product.category',
                                        'product_id',
                                        string="Shopify Categories",
                                        readonly=True)

    shopify_id = fields.Char(string="Shopify Id",
                             store=True, copy=False)
    shopify_inventory_id = fields.Char(
        string="Shopify Inventory Id", store=True, copy=False)
    shopify_type = fields.Char(string="Shopify Type",
                               readonly=True, store=True)
    shopify_com = fields.Char(string='shopify_com', )
    shopify_image_id = fields.Char(string="Shopify Image Id",
                                   store=True, copy=False)

    ###################################################################################
    shopify_origin_country_id = fields.Many2one(
        string='Shopify Country Code of Origin',
        comodel_name='res.country',
        ondelete='restrict',
    )
    shopify_province_origin_id = fields.Many2one(
        string='Shopify Province Code of Origin',
        comodel_name='res.country.state',
        ondelete='restrict',
    )
    ###################################################################################
    #Currency Conversion
    shopify_currency_id = fields.Many2one(
        string='Shopify Currency',
        comodel_name='res.currency',
        ondelete='restrict',
    )
    shopify_price = fields.Float(
        string='Shopify Product Price',
    )
    
    def computer_shopify_price(self):
        for rec in self:
            rec.shopify_price = rec.list_price
            if rec.shopify_currency_id:
                if rec.shopify_currency_id != rec.currency_id:
                    rec.shopify_price = rec.list_price*rec.shopify_currency_id.rate




    @api.depends('product_template_attribute_value_ids')
    def _compute_combination_indices(self):
        for product in self:
            product.combination_indices = product.product_template_attribute_value_ids._ids2str()
            if product.product_template_attribute_value_ids._ids2str() == '' and product.marketplace_type == 'shopify':
                product.combination_indices = product.shopify_com

    compare_at_price = fields.Char(string='compare_at_price', )
    fulfillment_service = fields.Char(string='fulfillment_service', )
    inventory_management = fields.Char(string='inventory_management', )
    inventory_policy = fields.Char(string='inventory_policy', )
    requires_shipping = fields.Boolean(
        string='requires_shipping',
    )
    taxable = fields.Boolean(
        string='taxable',
    )

    shopify_vendor = fields.Char()
    shopify_collections = fields.Char()

    def action_create_shopify_product(self):
        data = get_protmpl_vals(self, {})
        _logger.info("data ===>>>", data)
        shopify_pt_request(self, data, 'create')

    def action_update_shopify_product(self):
        data = get_protmpl_vals(self, {})
        res = shopify_pt_request(self, data, 'update')
        print("RES====>>>>", res)

    def action_update_inventory_item(self):
        for rec in self:
            if rec.shopify_inventory_id:
                ############################################################################
                # {
                #     "inventory_item": {
                #         "cost": "25.00",
                #         "country_code_of_origin": "FR",
                #         "country_harmonized_system_codes": [
                #             {
                #                 "country_code": "CA",
                #                 "harmonized_system_code": "1234561111"
                #             },
                #             {
                #                 "country_code": "US",
                #                 "harmonized_system_code": "1234562222"
                #             }
                #         ],
                #         "created_at": "2012-08-24T14:01:47-04:00",
                #         "harmonized_system_code": 123456,
                #         "id": 450789469,
                #         "province_code_of_origin": "QC",
                #         "sku": "IPOD2008PINK",
                #         "tracked": true,
                #         "updated_at": "2012-08-24T14:01:47-04:00",
                #         "requires_shipping": true
                #     }
                # }
                ############################################################################
                inventory_item = {
                    "id": rec.shopify_inventory_id,
                    "sku": rec.default_code,
                }
                if rec.shopify_compare_price:
                    inventory_item['cost'] = rec.shopify_compare_price if rec.shopify_compare_price else None
                try:
                    inventory_item['harmonized_system_code'] = rec.x_studio_custom_hscode if rec.x_studio_custom_hscode else None
                except Exception as e:
                    inventory_item['harmonized_system_code'] = rec.hs_code
                if rec.detailed_type in ['product', 'consumable']:
                    inventory_item['requires_shipping'] = True
                if rec.shopify_origin_country_id:
                    inventory_item['country_code_of_origin'] = rec.shopify_origin_country_id.code if rec.shopify_origin_country_id else None
                    if inventory_item.get('harmonized_system_code'):
                        inventory_item['country_harmonized_system_codes'] = [{
                                    "country_code": rec.shopify_origin_country_id.code,
                                    "harmonized_system_code": inventory_item['harmonized_system_code']
                        }]
                if rec.shopify_province_origin_id:
                    inventory_item['province_code_of_origin'] = rec.shopify_province_origin_id.code if rec.shopify_province_origin_id else None
             
                inventory_item = {k: v for k, v in inventory_item.items() if v}
                data = {"inventory_item": inventory_item}
                data = {k: v for k, v in data.items() if v}
                _logger.info("data====>>>>%s" %data)
                res = shopify_inventory_request(self, data, 'update')
                _logger.info("RES====>>>>%s" %res)
            else:
                rec.message_post(
                    body=_("Shopify Inventory Id is Empty for Product-%s" % (rec.id)))

    @api.model
    def create(self, values):
        """
            Create a new record for a model ModelName
            @param values: provides a data for new record

            @return: returns ProductTemplateShopify id of new record
        """
        result = super(ProductProductShopify, self).create(values)
        if values.get('product_tmpl_id'):
            """Create a Products"""
            product_tmpl_id = self.env['product.template'].sudo().search([('id', '=', values.get('product_tmpl_id'))],
                                                                         limit=1)
            values['marketplace_type'] = product_tmpl_id.marketplace_type if product_tmpl_id.marketplace_type else None
        ######################################################################################################################
        # if values.get('shopify_id'):
        #     ProTmpl = self.env['product.product'].sudo()
        #     product = ProTmpl.search(
        #         [('shopify_id', '=', values.get('shopify_id'))], limit=1)
        #     if product:
        #         _logger.warning(
        #             "Product already exists with id=%s and shopify id = %s", product.id, product.shopify_id)
        #         return product.id
        #     else:
        #         result = super(ProductProductShopify, self).create(values)

        # else:
        #     result = super(ProductProductShopify, self).create(values)
        ######################################################################################################################
        return result


class ProductCategshopify(models.Model):
    _inherit = 'product.category'

    marketplace_type = fields.Selection(
        selection_add=[('shopify', 'Shopify')]
    )
    shopify_id = fields.Integer(string="shopify id of the category",
                                readonly=True,
                                store=True)


class ShopifyCategory(models.Model):
    _name = 'shopify.product.category'
    _description = 'shopify Product Category'
    _rec_name = 'categ_name'

    name = fields.Many2one('product.category', string="Category")
    categ_name = fields.Char(string="Actual Name")
    product_tmpl_id = fields.Many2one(
        'product.template', string="Product Template Id")
    product_id = fields.Many2one('product.product', string="Product")


class ProductAttributeValueExtended(models.Model):
    _inherit = 'product.attribute.value'

    marketplace_type = fields.Selection(
        selection_add=[('shopify', 'Shopify')]
    )


# class ProductAttributeSet(models.Model):
#     _name = 'product.attribute.set'
#     _description = 'Product Attribute Set'

#     marketplace_type = fields.Selection(
#         selection_add=[('shopify', 'Shopify')]
#     )

#     name = fields.Char('Attribute Set')
#     code = fields.Char('Code')
#     attribute_rel = fields.One2many(
#         'product.attribute', 'attribute_set', string="Attributes")


class ProductAttributeExtended(models.Model):
    _inherit = 'product.attribute'

    marketplace_type = fields.Selection(
        selection_add=[('shopify', 'Shopify')]
    )
    attribute_set_id = fields.Integer(string="Ids")
    # attribute_set = fields.Many2one('product.attribute.set')


# class ProductImaget(models.Model):
#     _inherit = 'product.image'

#     marketplace_type = fields.Selection([], string="Marketplace Type")

class ProductAttributeExtended(models.Model):
    _inherit = 'product.attribute'

    marketplace_type = fields.Selection(
        selection_add=[('shopify', 'Shopify')]
    )


class ProductAttributeValueExtended(models.Model):
    _inherit = 'product.attribute.value'

    marketplace_type = fields.Selection(
        selection_add=[('shopify', 'Shopify')]
    )


class PTAL(models.Model):
    _inherit = 'product.template.attribute.line'

    marketplace_type = fields.Selection(
        selection_add=[('shopify', 'Shopify')]
    )


class SCPQ(models.TransientModel):
    _inherit = 'stock.change.product.qty'

    marketplace_type = fields.Selection(
        selection_add=[('shopify', 'Shopify')]
    )
