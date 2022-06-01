# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from jsonschema import ValidationError
from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import clean_context, OrderedSet
import requests
import json

from random import randrange

class StockPicking(models.Model):
    _inherit = "stock.picking"

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('push_3pl', 'Pushed to 3PL'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', compute='_compute_state',
        copy=False, index=True, readonly=True, store=True, tracking=True,
        help=" * Draft: The transfer is not confirmed yet. Reservation doesn't apply.\n"
             " * Waiting another operation: This transfer is waiting for another operation before being ready.\n"
             " * Push to 3PL: This transfer is integrated/pushed with/to 3PL.\n"
             " * Waiting: The transfer is waiting for the availability of some products.\n(a) The shipping policy is \"As soon as possible\": no product could be reserved.\n(b) The shipping policy is \"When all products are ready\": not all the products could be reserved.\n"
             " * Ready: The transfer is ready to be processed.\n(a) The shipping policy is \"As soon as possible\": at least one product has been reserved.\n(b) The shipping policy is \"When all products are ready\": all product have been reserved.\n"
             " * Done: The transfer has been processed.\n"
             " * Cancelled: The transfer has been cancelled.")
    threeplId = fields.Integer(string="3PL ID")
    tracking_3pl = fields.Char(string="Tracking Number 3PL")

    def get_3pl_warehouse_from_locations(self, source_location_obj, dest_location_obj):
        warehouse_ids = []
        warehouse_ids.append(source_location_obj.warehouse_id.id)
        warehouse_ids.append(dest_location_obj.warehouse_id.id)
        instance = self.env['instance.3pl'].search([], limit=1)
        for facility in instance.facilities_ids:
            if facility.warehouse_id.id in warehouse_ids:
                return facility.facilityId
        return False

    def action_push_to_3pl(self):
        source_warehouse = self.get_3pl_warehouse_from_locations(self.location_id, self.location_dest_id)
        if source_warehouse:
            self.export_picking_to_3pl(source_warehouse)
            self.state = 'push_3pl'
        
    def export_picking_to_3pl(self, source_warehouse):
        print("export_picking_to_3pl")
        if self.state in ('waiting', 'confirmed', 'assigned'):
            instance = self.env['instance.3pl'].search([], limit=1)
            url = "https://secure-wms.com/orders"
            #orderItems
            orderItems = []
            for line in self.move_ids_without_package:
                orderItems.append(
                        {
                        "itemIdentifier": {
                            "sku": line.product_id.default_code
                        },
                        "qty": line.quantity_done
                        }
                )
            #END orderItems

            payload = json.dumps({
                "customerIdentifier": {
                    "id": instance.customerId
                },
                "facilityIdentifier": {
                    "id": source_warehouse
                },
                "referenceNum": self.name + str(randrange(10)),
                "notes": '',
                "shippingNotes": '',
                "billingCode": "Prepaid",
                "routingInfo": {
                    "carrier": "UPS",
                    "mode": "92"
                },
                "shipTo": {
                    "companyName": self.partner_id.name,
                    "name": self.partner_id.name,
                    "address1": self.partner_id.street,
                    "address2": self.partner_id.street2,
                    "city": self.partner_id.city,
                    "state": self.partner_id.state_id.name,
                    "zip": self.partner_id.zip,
                    "country": self.partner_id.country_id.code
                },
                'soldTo': {
                    'sameAs': 0
                },
                "orderItems": orderItems
                })
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/hal+json',
                'Authorization': 'Bearer ' + str(instance.access_token)
                }
            response = requests.request("POST", url, headers=headers, data=payload)
            res_dict = self.button_validate()
            if type(res_dict) != bool:
                self.env['stock.backorder.confirmation'].with_context(res_dict['context']).process()
            if response.status_code == 201:
                response = json.loads(response.text)
                self.threeplId = response.get('readOnly').get('orderId')
            else:
                raise UserError(response.text)
        else:
            raise UserError("Only Order in Waiting and Ready state can be pushed to 3PL.")

    def update_picking_from_3pl(self):
        print("update_picking_from_3pl")
        instance = self.env['instance.3pl'].search([], limit=1)
        url = "https://secure-wms.com/orders/{}".format(self.threeplId)

        headers = {
            'Host': 'secure-wms.com',
            'Accept-Language': 'en-US,en;q=0.8',
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/hal+json',
            'Authorization': 'Bearer ' + str(instance.access_token)
        }
        response = requests.request("GET", url, headers=headers, data={})
        print(response.status_code)
        if response.status_code == 200:
            response = json.loads(response.text)
            print(response)
            is_closed = response.get('readOnly').get('isClosed')
            status = response.get('readOnly').get('status')
            fully_allocated = response.get('readOnly').get('fullyAllocated')
            print(is_closed)
            print(status)
            # CANCEL ORDER
            if is_closed and status == 2:
                if self.state == 'push_3pl':
                    self.action_cancel()
            # CLOSED ORDER
            if is_closed and status == 1 and fully_allocated:
                tracking_number = response.get('routingInfo').get('trackingNumber')
                self.tracking_3pl = tracking_number
                items_dict = self.get_order_item_3pl(self.threeplId)
                dict_item_to_create_backorder_lines = {}
                for item in items_dict:
                    item_3pl_id = item.get('itemIdentifier').get('id')
                    item_qty = item.get('qty')
                    item_odoo_id = self.env['product.product'].search([('product_3pl_id', '=', item_3pl_id)])
                    if not item_odoo_id:
                        raise UserError('Can not find the product with 3pl id: ' + str(item_3pl_id))
                    res_item = self.move_line_ids_without_package.filtered(lambda l: l.product_id == item_odoo_id)
                    if not res_item:
                        raise UserError(
                            'Can not find move_line_ids_without_package with product_id: ' + str(item_odoo_id.id))
                    if res_item.qty_done != item_qty:
                        dict_item_to_create_backorder_lines[item_odoo_id.id] = res_item.qty_done - item_qty
                        res_item.write({'qty_done': item_qty})
                if dict_item_to_create_backorder_lines:
                    new_backorder = self.copy()
                    new_backorder.threeplId = ''
                    list_product = list(dict_item_to_create_backorder_lines.keys())
                    for line in new_backorder.move_ids_without_package:
                        if line.product_id.id not in list_product:
                            line.unlink()
                        else:
                            line.product_uom_qty = dict_item_to_create_backorder_lines.get(line.product_id.id)
                    self.message_post(
                        body=_(
                            'The backorder <a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a> has been created.') % (
                                 new_backorder.id, new_backorder.name))
                self.state = 'done'
        else:
            raise UserError(response.text)

    def get_order_item_3pl(self, order_id):
        instance = self.env['instance.3pl'].search([], limit=1)
        url = "https://secure-wms.com/orders/{}/items".format(order_id)

        headers = {
            'Host': 'secure-wms.com',
            'Accept-Language': 'en-US,en;q=0.8',
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/hal+json',
            'Authorization': 'Bearer ' + str(instance.access_token)
        }
        response = requests.request("GET", url, headers=headers, data={})
        if response.status_code == 200:
            response = json.loads(response.text)
            print(json.dumps(response, indent=2))
            return response.get('_embedded').get('http://api.3plCentral.com/rels/orders/item')
        else:
            raise UserError(response.text)