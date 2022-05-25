from odoo import models, fields
import requests, json
from requests.auth import HTTPBasicAuth
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class ProductProduct(models.Model):
    _inherit = "product.product"

    length = fields.Float('Length', tracking=True)
    width = fields.Float('Width', tracking=True)
    height = fields.Float('Height', tracking=True)

    is_haz_mat = fields.Boolean('Is Haz Mat')
    haz_mat_id = fields.Char('Haz Mat ID')
    haz_mat_shipping_name = fields.Char('Haz Mat Shipping Name')

    product_3pl_id = fields.Char('3PL Item ID')

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
                            "Id": 1
                        }
                    }
                }
            }
            if record.barcode:
                payload["upc"] = record.barcode
            if record.is_haz_mat:
                payload["options"]["hazMat"] = dict(
                    isHazMat=str(True),
                    id=record.haz_mat_id,
                    shippingName=record.haz_mat_shipping_name
                )
            payload = str(payload)
            response = requests.request("POST", url, headers=headers, data=payload)
            if response.status_code == 201:
                response = json.loads(response.text)
                try:
                    record.product_3pl_id = response["itemId"]
                except Exception as e:
                    _logger.info(e)
                    raise UserError(e)
            else:
                _logger.info(response.text)
                raise UserError(response.text)