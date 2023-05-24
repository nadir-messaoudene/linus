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
                'product_data': item,
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
                if not product_id:
                    product_id = self.env['product.product'].search([('default_code', '=', feed.custom_sku)])
                if product_id:
                    _logger.info(vals)
                    product_id.write(vals)
                else:
                    # vals['name'] = feed.name
                    # vals['detailed_type'] = 'product'
                    # vals['active'] = True
                    # vals['sale_ok'] = True
                    # vals['purchase_ok'] = True
                    # vals['default_code'] = feed.custom_sku
                    # vals['barcode'] = feed.upc
                    # categ_id = self.env['product.category'].search([('name', '=', category.name)])
                    # vals['categ_id'] = categ_id.id
                    # product_id = self.env['product.template'].create(vals)
                    raise ValidationError(f'Cannot find productid {feed.lightspeed_item_id}')
                feed.state = 'done'
            except Exception as e:
                feed.state = 'error'
                err_message = f'Product Feed {feed.name} [{feed.custom_sku}]. Error: {str(e)}'
                feed.message += err_message
                _logger.info(err_message)
                continue
