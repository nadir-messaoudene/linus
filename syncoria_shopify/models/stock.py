
# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import pprint
import re
from ..shopify.utils import *
from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    
    shopify_track_updated = fields.Boolean(
        string='Shopify Track Updated',
        default=False,
        readonly=True,
    )
    
    marketplace_type = fields.Char(
        string='Marketplace Type',
        compute='_compute_marketplace_type' )
        
    @api.depends('origin')
    def _compute_marketplace_type(self):
        for record in self:
            sale_order = self.env['sale.order'].sudo().search([('name','=',record.origin)], limit=1)
            if sale_order:
                record.marketplace_type = sale_order.marketplace_type
        

    def action_validate(self):
        print("Shopify---<>action_validate")
        result = super(StockPicking, self).action_validate()
        self.create_shopify_fulfillment()
        return result

    def create_shopify_fulfillment(self):
        """
            Action to create Fullfillments with Tracking Number and Tracking URL
        """
        fullfillment = {}
        # Fulfill all line items for an order and send the shipping confirmation email. Not specifying line item IDs causes all unfulfilled and partially fulfilled line items for the order to be fulfilled.
        # POST /admin/api/2021-07/orders/450789469/fulfillments.json
        SaleOrder = self.env['sale.order'].sudo()
        marketplace_instance_id = get_marketplace(self)
        sp_order_id = SaleOrder.search([('name', '=', self.origin)], limit=1)
        # return self.get_shopify_locations(marketplace_instance_id, sp_order_id)
        if sp_order_id and sp_order_id.marketplace_type == 'shopify':
            data = self.get_fullfillment_data(sp_order_id)
            version = marketplace_instance_id.marketplace_api_version or '2021-01'
            url = marketplace_instance_id.marketplace_host + \
                '/admin/api/%s/orders/%s/fullfillments.json' % (
                    version, sp_order_id.shopify_id)
            headers = {
                'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
                'Content-Type': 'application/json'
            }
            type_req = 'POST'
            fullfillment = self.env[
                'marketplace.connector'].shopify_api_call(
                headers=headers,
                url=url,
                type=type_req,
                marketplace_instance_id=marketplace_instance_id,
                data=data
            )
            print("fullfillment")
            print(fullfillment)

            if fullfillment.get('errors'):
                raise exceptions.UserError(_(fullfillment.get('errors')))
            else:
                self.write({'shopify_track_updated':True})

        return fullfillment

    def get_fullfillment_data(self, sp_order_id):
        marketplace_instance_id = get_marketplace(self)
        fullfillment = {}
        fullfillment['message'] = "The package is being shipped today."
        if self.carrier_tracking_ref:
            if len(self.carrier_tracking_ref.split(",")) > 1:
                fullfillment['tracking_numbers'] = []
                for t_no in self.carrier_tracking_ref.split(","):
                    fullfillment['tracking_numbers'].append(t_no)

            if len(self.carrier_tracking_ref.split(",")) == 1:
                fullfillment['tracking_number'] = self.carrier_tracking_ref

        if self.carrier_tracking_url:
            if len(self.carrier_tracking_url.split(",")) > 1:
                fullfillment['tracking_numbers'] = []
                for url in self.carrier_tracking_url.split(","):
                    fullfillment['tracking_urls'].append(url)

            if len(self.carrier_tracking_ref.split(",")) == 1:
                fullfillment['tracking_url'] = self.carrier_tracking_url

        fullfillment["tracking_company"] = "Purolator" #self.carrier_id.delviery_type if self.carrier_id else None
        fullfillment.update({
            "location_id": 61532176569,
            "notify_customer": marketplace_instance_id.notify_customer or False
        })
        fullfillment = {
            "fulfillment": fullfillment
        }
        fullfillment = {
           "fulfillment":
                {
                    "message":"The package was shipped this morning.",
                    "notify_customer":False,
                    "tracking_info":
                    {
                        "number":123456789,
                        "url":"https:\/\/www.my-shipping-company.com",
                        "company":"my-shipping-company"
                    },
                    "line_items_by_fulfillment_order":
                    [
                        {
                            "fulfillment_order_id" : sp_order_id.shopify_id,
                            "fulfillment_order_line_items":
                            [
                                # {
                                #     "id": sp_order_id.order_line[0].shopify_id,
                                #     "quantity":1
                                # }
                            ]
                        }
                    ]
                }
            }


        return fullfillment

    def get_shopify_locations(self, marketplace_instance_id, sp_order_id):
        marketplace_instance_id = get_marketplace(self)
        if sp_order_id and sp_order_id.marketplace_type == 'shopify':
            version = marketplace_instance_id.marketplace_api_version or '2021-01'
            url = marketplace_instance_id.marketplace_host + \
                '/admin/api/%s/locations.json' % (
                    version)
            headers = {
                'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
                'Content-Type': 'application/json'
            }
            type_req = 'GET'
            fullfillment = self.env[
                'marketplace.connector'].shopify_api_call(
                headers=headers,
                url=url,
                type=type_req,
                marketplace_instance_id=marketplace_instance_id,
                data={}
            )
            _logger.info("\nfullfillment---->" + str(fullfillment))

            if fullfillment.get('errors'):
                raise exceptions.UserError(_(fullfillment.get('errors')))
            else:
                _logger.info("\nSuccess---->")

    def get_order_fullfillments(self):
        marketplace_instance_id = get_marketplace(self)
        SaleOrder = self.env['sale.order'].sudo()
        sp_order_id = SaleOrder.search([('name', '=', self.origin)], limit=1)

        if sp_order_id and sp_order_id.marketplace_type == 'shopify':
            version = marketplace_instance_id.marketplace_api_version or '2021-01'
            url = marketplace_instance_id.marketplace_host + \
                '/admin/api/%s/fulfillment_orders/%s/fulfillments.json' % (
                    version, sp_order_id.shopify_id)
            headers = {
                'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
                'Content-Type': 'application/json'
            }
            type_req = 'GET'
            fullfillment = self.env[
                'marketplace.connector'].shopify_api_call(
                headers=headers,
                url=url,
                type=type_req,
                marketplace_instance_id=marketplace_instance_id,
                data={}
            )
            _logger.info("\nfullfillment---->" + str(fullfillment))

            if fullfillment.get('errors'):
                raise exceptions.UserError(_(fullfillment.get('errors')))
            else:
                _logger.info("\nSuccess---->")

class  InheritedStockwarehouse(models.Model):
    _inherit = 'stock.warehouse'

    shopify_warehouse_id = fields.Char(related='shopify_warehouse.shopify_invent_id',string="Shopify Warehouse ID",
                                       store=True,
                                       readonly=True,
                                       )
    shopify_warehouse_active = fields.Boolean(related='shopify_warehouse.shopify_loc_active',store=True,
                                       readonly=True,)

    shopify_warehouse = fields.Many2one("shopify.warehouse",string="Shopify Warehouse",help="If this field have value it will update qty of product/product variants.If not set value it will only update price. ")


    @api.onchange('shopify_warehouse')
    def _partner_id_change(self):
        if self.shopify_warehouse.partner_id:
            self.partner_id = self.shopify_warehouse.partner_id
    shopify_warehouse_id = fields.Char(related='partner_id.shopify_warehouse_id',string="Shopify Warehouse ID",
                                       store=True,
                                       readonly=True,
                                       )
    shopify_warehouse_active = fields.Boolean(related='partner_id.shopify_warehouse_active',store=True,
                                       readonly=True,)
