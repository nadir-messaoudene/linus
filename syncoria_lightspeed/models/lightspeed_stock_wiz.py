from odoo import models, fields, exceptions, _, api
import logging
_logger = logging.getLogger(__name__)


class LightspeedStockWiz(models.TransientModel):
    _name = 'lightspeed.stock.wiz'
    _description = 'Stock Update Wizard Lightspeed'

    fetch_type = fields.Selection([('from_odoo', 'From Odoo to Lightspeed')], string="Operation Type")
    source_location_ids = fields.Many2many('stock.location', string="Source Location")
    instance_id = fields.Many2one(string='Lightspeed Instance', comodel_name='lightspeed.instance')

    def lightspeed_update_stock_item(self):
        active_ids = self._context.get('active_ids')
        products = self._shopify_get_product_list(active_ids)
        print(products)
        for product in products:
            load_relations = '?load_relations=["ItemShops"]'
            url = 'Item/{}.json'.format(product.lightspeed_item_id)
            res = self.instance_id.get_request(self.instance_id.base_url + url + load_relations)
            if res.get('Item', {}).get('ItemShops'):
                res = res.get('Item')
                if type(res.get('ItemShops').get('ItemShop')) is dict:
                    item_shop_list = [res.get('ItemShops').get('ItemShop')]
                else:
                    item_shop_list = res.get('ItemShops').get('ItemShop')
                for item_shop in item_shop_list:
                    if item_shop.get('shopID') != '0':
                        qoh = product.with_context({"location": self.source_location_ids.ids}).free_qty
                        data = {
                            "ItemShops": {
                                "ItemShop": {
                                    "itemShopID": item_shop.get('itemShopID'),
                                    "qoh": qoh if qoh > 0 else 0
                                }
                            }
                        }
                        self.instance_id.put_request(self.instance_id.base_url + url + load_relations, data)

    def _shopify_get_product_list(self, active_ids):
        if self._context.get('active_model') == 'product.product':
            products = self.env['product.product'].search([
                ('lightspeed_item_id', '!=', ''),
                ('id', 'in', active_ids)
            ])
        if self._context.get('active_model') == 'product.template':
            products = self.env['product.product'].search([
                ('lightspeed_item_id', '!=', ''),
                ('product_tmpl_id', 'in', active_ids)
            ])
        return products
