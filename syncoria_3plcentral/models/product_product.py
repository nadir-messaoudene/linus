from odoo import models, fields, api, _
import requests, json
from requests.auth import HTTPBasicAuth
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class ProductWarehouse3PL(models.Model):
    _name = "product.warehouse.3pl"

    name = fields.Char('Name')
    product_id = fields.Many2one('product.product', 'Product')
    warehouse_name = fields.Char('Warehouse Name')
    quantity = fields.Integer('Quantity')

class ProductProduct(models.Model):
    _inherit = "product.product"

    length = fields.Float('3PL Length', tracking=True)
    width = fields.Float('3PL Width', tracking=True)
    height = fields.Float('3PL Height', tracking=True)

    is_haz_mat = fields.Boolean('Is Haz Mat')
    haz_mat_id = fields.Char('Haz Mat ID')
    haz_mat_shipping_name = fields.Char('Haz Mat Shipping Name')

    product_3pl_id = fields.Char('3PL Item ID')
    measure_type_id = fields.Many2one('measure.types', 'Packaging Unit')
    unit_qty = fields.Integer('Packing UOM Qty')
    product_warehouse_3pl_ids = fields.One2many('product.warehouse.3pl', 'product_id', 'Product Warehouse 3PL')
    product_warehouse_3pl_count = fields.Integer('Product Warehouse 3PL Count', compute='_compute_total_qty')

    @api.depends('product_warehouse_3pl_ids')
    def _compute_total_qty(self):
        for record in self:
            record.product_warehouse_3pl_count = 0
            for each_warehouse in record.product_warehouse_3pl_ids:
                record.product_warehouse_3pl_count += each_warehouse.quantity

    def get_root_category_name(self):
        if self.categ_id.parent_id:
            return self.categ_id.parent_id.name
        else:
            return self.categ_id.name

    def get_first_package(self):
        if self.packaging_ids:
            return [self.packaging_ids[0].name, self.packaging_ids[0].qty]
        else:
            return ['','']

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
                "description": record.display_name.replace('[{}] '.format(record.default_code), ''),
                "description2": record.get_root_category_name(),
                "options": {
                    "inventoryUnit": {
                        "unitIdentifier": {
                            "Id": 1
                        }
                    },
                    "PackageUnit": {
                        "Imperial": {
                            "Length": record.length,
                            "Width": record.width,
                            "Height": record.height,
                            "Weight": record.weight
                        },
                        "UnitIdentifier": {
                            "name": record.measure_type_id.name,
                        },
                        "InventoryUnitsPerUnit": record.unit_qty
                    },
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
            print(payload)
            response = requests.request("POST", url, headers=headers, data=json.dumps(payload))
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

    def update_product_to_3pl(self):
        instance = self.env['instance.3pl'].search([], limit=1)

        for record in self:
            url = "https://secure-wms.com/customers/{}/items/{}".format(instance.customerId, record.product_3pl_id)
            # GET Item to get Etag
            payload = {}
            headers = {
                'Host': 'secure-wms.com',
                'Content-Type': 'application/json',
                'Accept': 'application/hal+json',
                'Authorization': 'Bearer ' + str(instance.access_token)
            }

            response = requests.request("GET", url, headers=headers, data=payload)
            if response.status_code == 200:
                etag = response.headers['ETag']
                res_dict = json.loads(response.text)
            else:
                _logger.info(response.text)
                raise UserError(response.text)
            ##########################################
            headers = {
                'Host': 'secure-wms.com',
                'Content-Type': 'application/json',
                'Accept': 'application/hal+json',
                'Authorization': 'Bearer ' + str(instance.access_token),
                'If-Match': etag
            }
            res_dict["sku"] = record.default_code
            res_dict["description"] = record.display_name.replace('[{}] '.format(record.default_code), '')
            res_dict["description2"] = record.get_root_category_name()
            res_dict["options"]['packageUnit'] = {
                "imperial": {
                    "Length": record.length,
                    "Width": record.width,
                    "Height": record.height,
                    "Weight": record.weight
                },
                "unitIdentifier": {
                    "name": record.measure_type_id.name,
                },
                "inventoryUnitsPerUnit": record.unit_qty
            }
            res_dict.pop('_links')
            res_dict.pop('_embedded')
            if record.barcode:
                res_dict["upc"] = record.barcode
            if record.is_haz_mat:
                res_dict["options"]["hazMat"] = dict(
                    isHazMat=str(True),
                    id=record.haz_mat_id,
                    shippingName=record.haz_mat_shipping_name
                )
            print(res_dict)
            response = requests.request("PUT", url, headers=headers, data=json.dumps(res_dict))
            if response.status_code == 200:
                print(response)
            else:
                _logger.info(response.text)
                raise UserError(response.text)

    def action_open_3pl_quants(self):
        return {
            'name': 'Warehouse 3PL Stock: %s' % self.name,
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'product.warehouse.3pl',
            'domain': [('product_id', '=', self.id)],
        }

    def update_product_qty_from_3pl(self):
        instance = self.env['instance.3pl'].search([], limit=1)
        url = "https://secure-wms.com/inventory/stocksummaries?pgsiz=500&pgnum=1&rql=ItemId=={}".format(self.product_3pl_id)

        headers = {
            'Host': 'secure-wms.com',
            'Accept-Language': 'en-US,en;q=0.8',
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'application/hal+json',
            'Authorization': 'Bearer ' + str(instance.access_token)
        }

        response = requests.request("GET", url, headers=headers)
        if response.status_code == 200:
            response = json.loads(response.text)
            summaries = response.get('summaries')
            if self.product_warehouse_3pl_ids:
                self.product_warehouse_3pl_ids = [(5,0,0)]
            for each_warehouse in summaries:
                print(each_warehouse)
                fac = self.env['facilities.3pl'].search([('facilityId', '=', each_warehouse.get('facilityId')), ('instance_3pl_id', '=', instance.id)])
                # if not fac.warehouse_id:
                #     raise UserError('There is no warehouse mapping for facilityId: {}'.format(each_warehouse.get('facilityId')))
                self.env['product.warehouse.3pl'].create({
                    'name': each_warehouse.get('facilityId'),
                    'warehouse_name': fac.name,
                    'product_id': self.id,
                    'quantity': each_warehouse.get('onHand')
                })
        else:
            _logger.info(response.text)
            raise UserError(response.text)