import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import requests
import logging
import json
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

    def lightspeed_create_product(self):
        for record in self:
            vals = {
                "defaultCost": record.standard_price,
                "discountable": "true",
                "tax": "true",
                "itemType": "default",
                "serialized": "false",
                "description": record.name,
                "modelYear": "0",
                "upc": "",
                "ean": "",
                "customSku": record.default_code,
                "manufacturerSku": record.default_code,
                "publishToEcom": "false",
                # "categoryID": "1",
                # "taxClassID": "1",
                # "departmentID": "0",
                # "itemMatrixID": "0",
                # "manufacturerID": "0",
                # "seasonID": "0",
                # "defaultVendorID": "0",
                "Prices": {
                    "ItemPrice": [
                        {
                            "amount": record.lst_price,
                            "useTypeID": "1",
                            "useType": "Default"
                        },
                        {
                            "amount": record.lst_price,
                            "useTypeID": "2",
                            "useType": "MSRP"
                        },
                        {
                            "amount": record.lst_price,
                            "useTypeID": "3",
                            "useType": "Online"
                        }
                    ]}
            }
            lightspeed_instance = self.env['lightspeed.instance'].search([('state', '=', 'validate')], limit=1)
            if not lightspeed_instance:
                return
            url = lightspeed_instance.base_url + 'Item.json'
            try:
                headers = {
                    'Authorization': 'Bearer ' + lightspeed_instance.access_token
                }
                response = requests.request("POST", url, data=json.dumps(vals), headers=headers)
                res = json.loads(response.text)
                _logger.info(res)
                if response.status_code == 200:
                    if "Item" in res:
                        update_vals = {
                            'lightspeed_item_id': res.get('Item').get('itemID'),
                            'lightspeed_system_sku': res.get('Item').get('systemSku')

                        }
                        record.write(update_vals)
                else:
                    raise ValidationError(res)
            except Exception as e:
                raise ValidationError(e)
