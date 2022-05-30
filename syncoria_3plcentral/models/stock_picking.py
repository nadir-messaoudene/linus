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
                "referenceNum": self.name,
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
            #Is Closed 
            is_closed = response.get('readOnly').get('isClosed')
            status = response.get('readOnly').get('status')
            print(is_closed)
            print(status)

            #CANCEL ORDER
            if is_closed and status == 2:
                if self.state == 'push_3pl':
                    self.action_cancel()

            #CLOSED ORDER        
            # if is_closed and status == 0:
            #TODO: Replace this line by above line once going live
            # if not is_closed and status == 0:
                #TODO: Closed (Complete) -> Validate and Create BackOrder (If remain)

            
            
            




        else:
            raise UserError(response.text)