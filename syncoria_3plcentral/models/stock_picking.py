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
        ('push_3pl', 'Pushed to 3PL'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
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

    def action_push_to_3pl(self):
        print("action_push_to_3pl")
        try:
            self.export_picking_to_3pl()
            self.state = 'push_3pl'
        except:
            raise ValidationError("Can not push to 3PL.")
        
    def export_picking_to_3pl(self):
        print("export_picking_to_3pl")
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
                    "qty": line.product_uom_qty
                    }
            )
        #END orderItems

        payload = json.dumps({
            "customerIdentifier": {
                "id": instance.customerId
            },
            "facilityIdentifier": {
                "id": 657
            },
            "referenceNum": self.name,
            "notes": '',
            "shippingNotes": '',
            "billingCode": "Prepaid",
            "routingInfo": {
                "carrier": self.carrier_id.name,
                # "mode": "92",
                # "scacCode": "UPGN",
                # "account": "12345z"
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
        print(payload)
        response = requests.request("POST", url, headers=headers, data=payload)
        
        print(response.status_code)
        if response.status_code == 200:
            response = json.loads(response.text)
        else:
            raise UserError(response.text)


    def update_picking_from_3pl(self):
        print("update_picking_from_3pl")
        instance = self.env['instance.3pl'].search([], limit=1)
        url = "https://secure-wms.com/customers/{}/items".format(instance.customerId)

        headers = {
            'Host': 'secure-wms.com',
            'Accept-Language': 'en-US,en;q=0.8',
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/hal+json',
            'Authorization': 'Bearer ' + str(instance.access_token)
        }