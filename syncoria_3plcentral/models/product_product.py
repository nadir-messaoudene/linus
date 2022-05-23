from odoo import models, fields
import requests, json
from requests.auth import HTTPBasicAuth

class ProductProduct(models.Model):
    _inherit = "product.product"

    length = fields.Float('Length', tracking=True)
    width = fields.Float('Width', tracking=True)
    height = fields.Float('Height', tracking=True)

    is_haz_mat = fields.Boolean('Is Haz Mat')
    haz_mat_id = fields.Char('Haz Mat ID')
    haz_mat_shipping_name = fields.Char('Haz Mat Shipping Name')

    def export_product_to_3pl(self):
        instance = self.env['instance.3pl'].search([], limit=1)
        url = "https://secure-wms.com/customers/{}/items".format(instance.customerId)

        headers = {
            'Host': 'secure-wms.com',
            'Accept-Language': 'en-US,en;q=0.8',
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/hal+json',
            'Authorization': 'Bearer ' + str(instance.access_token)
        }
        for record in self:
            payload = {
                "sku": record.default_code,
                "description": record.display_name,
                "options": {
                    "inventoryUnit": {
                        "unitIdentifier": {
                            "name": "test"
                        }
                    }
                }
            }
            if record.barcode:
                payload["upc"] = record.barcode
            if record.is_haz_mat:

            response = requests.request("POST", url, headers=headers, data=payload)

            print(response.text)