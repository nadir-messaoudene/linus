
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

    shopify_id = fields.Char(string="Fulfillment ID", copy=False)
    shopify_order_id = fields.Char(string="Shopify Order ID", copy=False, readonly="1")
    shopify_status = fields.Char(copy=False, readonly="1")
    shopify_service = fields.Char(copy=False, readonly="1")
    shopify_track_updated = fields.Boolean(default=False, readonly=True, copy=False,)
    marketplace_type = fields.Selection(selection=[('shopify', 'Shopify')], default='shopify')
    shopify_instance_id = fields.Many2one("marketplace.instance", string="Shopify Instance ID")


    # def action_validate(self):
    #     result = super(StockPicking, self).action_validate()
    #     # self.create_shopify_fulfillment()
    #     return result

    def shopify_api_call(self, **kwargs):
        if kwargs.get('kwargs'):
            kwargs = kwargs.get('kwargs')
        if not kwargs:
            return

        type = kwargs.get('type') or 'GET'
        complete_url = 'https://' + kwargs.get('url')
        headers = kwargs.get('headers')
        data = json.dumps(kwargs.get('data')) if kwargs.get('data') else None
        _logger.info("Request DATA==>>>>>>>>>>>" + pprint.pformat(data))

        try:
            res = requests.request(
                type, complete_url, headers=headers, data=data)
            return res
        except Exception as e:
            _logger.info("Exception occured %s", e)
            raise exceptions.UserError(_("Error Occured 5 %s") % e)

    """ LEGACY """
    # def create_shopify_fulfillment(self):
    #     """
    #         Action to create Fullfillments with Tracking Number and Tracking URL
    #
    #         Fulfill all line items for an order and send the shipping confirmation email.
    #         Not specifying line item IDs causes all unfulfilled and
    #         partially fulfilled line items for the order to be fulfilled.
    #         POST /admin/api/2021-07/orders/450789469/fulfillments.json
    #     """
    #     _logger.info("Delivery Type===>>>{}".format(self.delivery_type))
    #     _logger.info("Picking Type Code===>>>{}".format(
    #         self.picking_type_id.code))
    #
    #     sale_order = self.env['sale.order'].sudo()
    #     # marketplace_instance_id = get_marketplace(self)
    #     sp_order_id = sale_order.search([('name', '=', self.origin)], limit=1)
    #     marketplace_instance_id = sp_order_id.shopify_instance_id
    #     if sp_order_id and sp_order_id.marketplace_type == 'shopify':
    #         data = self.get_fullfillment_data(sp_order_id)
    #         _logger.info("data===>>>{}".format(data))
    #         version = marketplace_instance_id.marketplace_api_version or '2022-01'
    #         url = marketplace_instance_id.marketplace_host + '/admin/api/%s/orders/%s/fulfillments.json' % (
    #                 version, sp_order_id.shopify_id)
    #         headers = {
    #             'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
    #             'Content-Type': 'application/json'
    #         }
    #         type_req = 'POST'
    #         res = self.shopify_api_call(
    #             headers=headers,
    #             url=url,
    #             type=type_req,
    #             marketplace_instance_id=marketplace_instance_id,
    #             data=data
    #         )
    #         if res.status_code == 201:
    #             _logger.info("""Successful Fulfillment""")
    #             res_json = res.json()
    #             if res_json.get('fulfillment'):
    #                 self.write({
    #                     'shopify_id' : res_json.get('fulfillment',{}).get('id'),
    #                     'shopify_order_id' : res_json.get('fulfillment',{}).get('order_id'),
    #                     'shopify_status' : res_json.get('fulfillment',{}).get('status'),
    #                     'shopify_service' : res_json.get('fulfillment',{}).get('service'),
    #                 })
    #             self.message_post(body=_("Successfull Shopify Fulfillment for Picking-{}, Fulfillment Id-{}".format(self, self.shopify_id)))
    #             self.shopify_track_updated = True
    #         else:
    #             raise exceptions.UserError(_("Exception-{}".format(res.text)))

    def get_fulfillment_order(self):
        for rec in self:
            marketplace_instance_id = rec.sale_id.shopify_instance_id
            url = marketplace_instance_id.marketplace_host + '/admin/api/%s/orders/%s/fulfillment_orders.json' % (
                marketplace_instance_id.marketplace_api_version, rec.sale_id.shopify_id)
            headers = {
                'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
                'Content-Type': 'application/json'
            }
            type_req = 'GET'
            fulfillment_orders = self.shopify_api_call(
                headers=headers,
                url=url,
                type=type_req,
                marketplace_instance_id=marketplace_instance_id,
            )
            if fulfillment_orders.status_code != 200:
                raise exceptions.UserError(_(fulfillment_orders.text))
            else:
                return fulfillment_orders.json()

    def create_shopify_fulfillment(self):
        """
            Action to create Fullfillments with Tracking Number and Tracking URL

            Fulfill all line items for an order and send the shipping confirmation email.
            Not specifying line item IDs causes all unfulfilled and
            partially fulfilled line items for the order to be fulfilled.
            POST /admin/api/2023-01/fulfillments.json
        """
        _logger.info("Delivery Type===>>>{}".format(self.delivery_type))
        _logger.info("Picking Type Code===>>>{}".format(self.picking_type_id.code))

        sp_order_id = self.sale_id
        marketplace_instance_id = sp_order_id.shopify_instance_id
        if sp_order_id and sp_order_id.marketplace_type == 'shopify':
            shopify_warehouse = self.location_id.shopify_warehouse_ids.filtered(
                lambda l: l.shopify_instance_id.id == marketplace_instance_id.id)
            shopify_inv_id = shopify_warehouse.shopify_invent_id
            if not shopify_warehouse:
                raise exceptions.ValidationError('This location has not been mapped')
            res = self.get_fulfillment_order()
            fulfillment_orders = res.get('fulfillment_orders')
            shopify_location_id = shopify_inv_id
            """
                IF LOCATION MATCHES, THAT MEANS WE ARE FULFILLING FROM THE RIGHT LOCATION
                IF NOT, WE HAVE TO MOVE THE LOCATION
            """
            fulfillment_order = False
            fulfillable_orders = [order for order in fulfillment_orders if
                                  order['status'] in ('open', 'in_progress', 'scheduled')]
            for fulfillment in fulfillable_orders:
                if fulfillment['assigned_location_id'] == int(shopify_location_id):
                    fulfillment_order = fulfillment
                    break
            if not fulfillment_order:
                fulfillment_order = self.move_shopify_fulfillment_order(fulfillable_orders, shopify_location_id)
            if fulfillment_order:
                fulfillment_order_id = fulfillment_order.get('id')
                line_items = fulfillment_order.get('line_items')
                line_map_dict = {}
                for line in line_items:
                    line_map_dict[str(line['line_item_id'])] = line['id']
                move_ids = self.move_lines.filtered(lambda m: m.quantity_done > 0)
                fulfillment_order_line_items = []
                for move in move_ids:
                    shopify_line_item_id = move.sale_line_id.shopify_id
                    fulfillment_order_line = {'id': line_map_dict.get(shopify_line_item_id, False),
                                              'quantity': int(move.quantity_done)}
                    if fulfillment_order_line.get('id'):
                        fulfillment_order_line_items.append(fulfillment_order_line)
                if move_ids:
                    fulfillment_dict = {
                        'message': 'The package was shipped',
                        'notify_customer': True,
                        'tracking_info': {'number': self.carrier_tracking_ref or '', 'url': self.carrier_tracking_url or ''},
                        'line_items_by_fulfillment_order': [{'fulfillment_order_id': fulfillment_order_id,
                                                             'fulfillment_order_line_items': fulfillment_order_line_items}]
                    }
                    version = marketplace_instance_id.marketplace_api_version or '2022-01'
                    url = marketplace_instance_id.marketplace_host + '/admin/api/%s/fulfillments.json' % (
                        version)
                    headers = {
                        'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
                        'Content-Type': 'application/json'
                    }
                    data = {
                        'fulfillment': fulfillment_dict
                    }
                    _logger.info("data===>>>{}".format(data))
                    type_req = 'POST'
                    res = self.shopify_api_call(
                        headers=headers,
                        url=url,
                        type=type_req,
                        marketplace_instance_id=marketplace_instance_id,
                        data=data
                    )
                    if res.status_code == 201:
                        _logger.info("""Successful Fulfillment""")
                        res_json = res.json()
                        if res_json.get('fulfillment'):
                            self.write({
                                'shopify_id': res_json.get('fulfillment', {}).get('id'),
                                'shopify_order_id': res_json.get('fulfillment', {}).get('order_id'),
                                'shopify_status': res_json.get('fulfillment', {}).get('status'),
                                'shopify_service': res_json.get('fulfillment', {}).get('service'),
                            })
                            self.message_post(body=_(
                                "Successfull Shopify Fulfillment for Picking-{}, Fulfillment Id-{}".format(self,
                                                                                                           self.shopify_id)))
                            self.shopify_track_updated = True
                    else:
                        self.message_post(body=res.text)

    def move_shopify_fulfillment_order(self, fulfillable_orders, shopify_location_id):
        self.ensure_one()
        for fulfillable_order in fulfillable_orders:
            marketplace_instance_id = self.sale_id.shopify_instance_id
            version = marketplace_instance_id.marketplace_api_version or '2023-01'
            url = marketplace_instance_id.marketplace_host + '/admin/api/%s/fulfillment_orders/%s/move.json' % (
                version, fulfillable_order['id'])
            headers = {
                'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
                'Content-Type': 'application/json'
            }
            data = {
                'fulfillment_order': {'new_location_id': int(shopify_location_id)}
            }
            res = self.shopify_api_call(
                headers=headers,
                url=url,
                type='POST',
                marketplace_instance_id=marketplace_instance_id,
                data=data
            )
            if res.status_code == 200:
                res_json = res.json()
                return res_json.get('moved_fulfillment_order')
            else:
                self.message_post(body=res.text)
                return False

    """ LEGACY"""
    # def get_fullfillment_data(self, sp_order_id):
    #     marketplace_instance_id=get_marketplace(self)
    #     fullfillment={}
    #     fullfillment['message']="The package is being shipped today."
    #
    #     if self.carrier_tracking_ref:
    #         if len(self.carrier_tracking_ref.split(",")) > 1:
    #             fullfillment['tracking_numbers']=[]
    #             for t_no in self.carrier_tracking_ref.split(","):
    #                 fullfillment['tracking_numbers'].append(t_no)
    #
    #         if len(self.carrier_tracking_ref.split(",")) == 1:
    #             fullfillment['tracking_number']=self.carrier_tracking_ref
    #
    #     if self.carrier_tracking_url:
    #         if len(self.carrier_tracking_url.split(",")) > 1:
    #             fullfillment['tracking_numbers']=[]
    #             for url in self.carrier_tracking_url.split(","):
    #                 fullfillment['tracking_urls'].append(url)
    #
    #         if len(self.carrier_tracking_ref.split(",")) == 1:
    #             fullfillment['tracking_url']=self.carrier_tracking_url
    #
    #     fullfillment["tracking_company"]=self.carrier_id.delivery_type if self.carrier_id else None
    #     SaleOrder = self.env['sale.order'].sudo()
    #     try:
    #         sp_order_obj = SaleOrder.search([('name', '=', self.origin)], limit=1)
    #         shopify_warehouse = self.location_id.shopify_warehouse_ids.filtered(lambda l: l.shopify_instance_id.id == sp_order_obj.shopify_instance_id.id)
    #         shopify_inv_id = shopify_warehouse.shopify_invent_id
    #     except:
    #         raise exceptions.UserError(_("The location is mapped to more than 1 warehouse of the same store"))
    #     fullfillment.update({
    #         "location_id": shopify_inv_id,
    #         "notify_customer": marketplace_instance_id.notify_customer or False
    #     })
    #
    #
    #     if self.sale_id and self.move_line_ids_without_package:
    #         fullfillment['line_items']=[]
    #         for line in self.move_line_ids_without_package:
    #             sale_line_id=self.sale_id.order_line.filtered(
    #                 lambda l: l.product_id.id == line.product_id.id)
    #             if sale_line_id:
    #                 fullfillment['line_items'].append({
    #                     'id': sale_line_id.shopify_id,
    #                     'quantity': line.qty_done,
    #                 })
    #
    #
    #     fullfillment= {k: v for k, v in fullfillment.items() if v is not None}
    #     fullfillment= {
    #         "fulfillment": fullfillment
    #     }
    #     return fullfillment

    def update_shopify_tracking(self):
        """"""

    def return_shopify_fulfillment(self):
        raise exceptions.UserError(_("Return Shopify Fullfillment Error. Please contact Developer.!"))

    def cancel_shopify_fulfillment(self):
        if self.shopify_id and self.state == 'draft':
            marketplace_instance_id = get_marketplace(self)
            version = marketplace_instance_id.marketplace_api_version or '2022-01'
            url = marketplace_instance_id.marketplace_host + '/admin/api/%s/fulfillments/%s/cancel.json' % (
                    version, self.shopify_id)
            headers = {
                'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
                'Content-Type': 'application/json'
            }
            type_req = 'POST'
            data = {}
            res = self.shopify_api_call(
                headers=headers,
                url=url,
                type=type_req,
                marketplace_instance_id=marketplace_instance_id,
                data=data
            )
            if res.status_code == 200:
                _logger.info("""Successful Cancel Fulfillment""")
                res_json = res.json()
                if res_json.get('fulfillment'):
                    self.write({
                        'shopify_id' : res_json.get('fulfillment',{}).get('id'),
                        'shopify_order_id' : res_json.get('fulfillment',{}).get('order_id'),
                        'shopify_status' : res_json.get('fulfillment',{}).get('status'),
                        'shopify_service' : res_json.get('fulfillment',{}).get('service'),
                    })
                self.message_post(body=_("Successfull Shopify Fulfillment Cancelled for Picking-{}, Fulfillment Id-{}".format(self, self.shopify_id)))

            else:
                raise exceptions.UserError(_("Exception-{}".format(res.text)))



    def get_shopify_locations(self, marketplace_instance_id, sp_order_id):
        marketplace_instance_id = get_marketplace(self)
        if sp_order_id and sp_order_id.marketplace_type == 'shopify':
            version = marketplace_instance_id.marketplace_api_version or '2021-01'
            url = marketplace_instance_id.marketplace_host + \
                '/admin/api/%s/locations.json' % (
                    version)
            headers={
                'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
                'Content-Type': 'application/json'
            }
            type_req = 'GET'
            fullfillment,next_link = self.env[
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

    # def get_order_fullfillments(self):
    #     marketplace_instance_id = get_marketplace(self)
        # SaleOrder = self.env['sale.order'].sudo()
        # sp_order_id = SaleOrder.search([('name', '=', self.origin)], limit=1)

    #     if sp_order_id and sp_order_id.marketplace_type == 'shopify':
    #         version = marketplace_instance_id.marketplace_api_version or '2022-01'
    #         url = marketplace_instance_id.marketplace_host + \
    #             '/admin/api/%s/fulfillment_orders/%s/fulfillments.json' % (
    #                 version, sp_order_id.shopify_id)
    #         headers = {
    #             'X-Shopify-Access-Token': marketplace_instance_id.marketplace_api_password,
    #             'Content-Type': 'application/json'
    #         }
    #         type_req = 'GET'
    #         fullfillment,next_link = self.env[
    #             'marketplace.connector'].shopify_api_call(
    #             headers=headers,
    #             url=url,
    #             type=type_req,
    #             marketplace_instance_id=marketplace_instance_id,
    #             data={}
    #         )
    #         _logger.info("\nfullfillment---->" + str(fullfillment))

    #         if fullfillment.get('errors'):
    #             raise exceptions.UserError(_(fullfillment.get('errors')))
    #         else:
    #             _logger.info("\nSuccess---->")
    def get_order_fullfillments(self):
        SaleOrder = self.env['sale.order'].sudo()
        sp_order_obj = SaleOrder.search([('name', '=', self.origin)], limit=1)
        sp_order_obj.get_order_fullfillments()

    def process_shopify_fulfilment(self):
        SaleOrder = self.env['sale.order'].sudo()
        sp_order_obj = SaleOrder.search([('name', '=', self.origin)], limit=1)
        sp_order_obj.process_shopify_fulfilment()

class  InheritedStockwarehouse(models.Model):
    _inherit = 'stock.warehouse'

    shopify_warehouse_id = fields.Char(related='shopify_warehouse.shopify_invent_id',string="Shopify Warehouse ID",
                                       store=True,
                                       readonly=True,
                                       )
    shopify_warehouse_active = fields.Boolean(string='Shopify Active', related='shopify_warehouse.shopify_loc_active',store=True,
                                       readonly=True,)

    shopify_warehouse = fields.Many2one("shopify.warehouse",string="Shopify Warehouse",help="If this field have value it will update qty of product/product variants.If not set value it will only update price. ")


    @api.onchange('shopify_warehouse')
    def _partner_id_change(self):
        if self.shopify_warehouse.partner_id:
            self.partner_id = self.shopify_warehouse.partner_id

class  InheritedStocklocation(models.Model):
    _inherit = 'stock.location'

    shopify_warehouse_ids = fields.Many2many("shopify.warehouse",string="Shopify Warehouse")


class InheritedStockMove(models.Model):
    _inherit = 'stock.move'

    def write(self, vals):
        res = super(InheritedStockMove, self).write(vals)
        for rec in self:
            if rec.state == 'done' and rec.product_id:
                rec.product_id.shopify_need_sync = True
        return res
