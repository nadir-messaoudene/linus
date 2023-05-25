import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class LightspeedProductFeeds(models.Model):
    _name = 'lightspeed.product.feeds'
    _description = 'Lightspeed Product Feeds'

    name = fields.Char(string='Name', required=True)
    instance_id = fields.Many2one(
        string='Lightspeed Instance',
        comodel_name='lightspeed.instance',
        ondelete='restrict',
    )
    product_data = fields.Text(readonly=1)
    state = fields.Selection(
        string='State',
        selection=[('draft', 'Draft'),
                   ('done', 'Done'),
                   ('error', 'Error')]
    )
    lightspeed_item_id = fields.Char(string='itemID', required=True)
    system_sku = fields.Char(string='systemSku')
    default_cost = fields.Float(string='defaultCost')
    discountable = fields.Boolean(string='discountable')
    taxable = fields.Boolean(string='tax')
    upc = fields.Char(string='upc')
    custom_sku = fields.Char(string='customSku')
    manufacturer_sku = fields.Char(string='manufacturerSku')
    tax_class_id = fields.Char(string='taxClassID')
    message = fields.Text(string='Logging')

    def create_feeds(self, item_list):
        for item in item_list:
            try:
                feed = self.create_feed(item)
                self += feed
            except Exception as e:
                _logger.info(e)
                continue
        return self

    def create_feed(self, item):
        try:
            _logger.info('Start creating/updating feeds for item: {} ({})'.format(item.get('description'), item.get('customSku')))
            vals = {
                'state': 'draft',
                'name': item.get('description'),
                'instance_id': self.env.context.get('instance_id').id,
                'product_data': json.dumps(item),
                'lightspeed_item_id': item.get('itemID'),
                'system_sku': item.get('systemSku'),
                'default_cost': item.get('defaultCost'),
                'discountable': True if item.get('discountable') == 'true' else False,
                'taxable': True if item.get('tax') == 'true' else False,
                'custom_sku': item.get('customSku'),
                'upc': item.get('upc'),
                'manufacturer_sku': item.get('manufacturerSku'),
                'tax_class_id': item.get('taxClassID'),
            }
            _logger.info(vals)
            item_feed_id = self.search([('lightspeed_item_id', '=', item.get('itemID'))])
            if item_feed_id:
                item_feed_id.write(vals)
            else:
                item_feed_id = self.create(vals)
            return item_feed_id
        except Exception as e:
            _logger.info(e)
            raise ValidationError(e)

    def evaluate_feed(self):
        for feed in self:
            try:
                _logger.info('Start evaluating feeds for item: {}'.format(feed.name))
                feed.message = ''
                vals = {'lightspeed_item_id': feed.lightspeed_item_id}
                product_id = self.env['product.product'].search([('lightspeed_item_id', '=', feed.lightspeed_item_id)])
                product = json.loads(feed.product_data)
                if not product_id:
                    product_id = self.env['product.product'].search([('default_code', '=', feed.custom_sku)])
                if product_id:
                    _logger.info("Product EXISTS")
                    _logger.info(product)
                    # product_id.write(vals)
                else:
                    category_data = product.get('Category')
                    prices = product.get('Prices')
                    amount = 0
                    for price in prices.get('ItemPrice'):
                        if price.get('useType') == 'Default':
                            amount = float(price.get('amount'))
                            break
                    vals = {
                        'lightspeed_item_id': product.get('itemID'),
                        'lightspeed_system_sku': product.get('systemSku'),
                        'standard_price': float(product.get('defaultCost')),
                        'taxable': product.get('taxable'),
                        'lightspeed_taxable': product.get('taxable'),
                        'lightspeed_discountable': product.get('discountable'),
                        'name': product.get('description'),
                        'lightspeed_upc': product.get('upc'),
                        'default_code': product.get('customSku'),
                        'lightspeed_manufacturer_sku': product.get('manufacturerSku'),
                        'lightspeed_publish_to_ecom': product.get('publishToEcom'),
                        'lightspeed_category_id': int(product.get('categoryID')),
                        'lightspeed_tax_class_id': int(product.get('taxClassID')),
                        'lst_price': amount,
                        'detailed_type': 'service' if product.get('itemType') == 'non_inventory' else 'product'
                    }
                    if self._context.get('fetch_prod'):
                        product_id = self.env['product.product'].create(vals)
                    else:
                        raise ValidationError(f'Cannot find productID {feed.lightspeed_item_id} {feed.custom_sku}')
                feed.state = 'done'
            except Exception as e:
                feed.state = 'error'
                err_message = f'Product Feed {feed.name} [{feed.custom_sku}]. Error: {str(e)}'
                feed.message += err_message
                _logger.info(err_message)
                continue
