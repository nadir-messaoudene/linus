import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class LightspeedOrderFeeds(models.Model):
    _name = 'lightspeed.order.feeds'
    _description = 'Lightspeed Order Feeds'

    _order = 'name DESC'

    name = fields.Char(string='Name', required=True, copy=False)
    instance_id = fields.Many2one(
        string='Lightspeed Instance',
        comodel_name='lightspeed.instance',
        ondelete='restrict',
        required=True
    )
    order_data = fields.Text(string='Order Data', readonly=1)
    state = fields.Selection(
        string='State',
        selection=[('draft', 'Draft'),
                   ('done', 'Done'),
                   ('error', 'Error')],
        default='draft'
    )
    completed = fields.Boolean(string='Completed')
    sale_id = fields.Char(string='Sale ID')
    reference_number = fields.Char(string='Reference Number')
    reference_number_source = fields.Char(string='Reference Number Source')
    ticket_number = fields.Char(string='Ticket Number')
    total = fields.Float(string='Total')
    discount = fields.Float(string='Discount')
    tax_amount = fields.Float(string='Tax Amount')
    payment_amount = fields.Float(string='Payment Amount')
    tips = fields.Float(string='Tips')
    customer_id = fields.Char(string='Customer ID')
    employee_id = fields.Char(string='Employee ID')
    shop_id = fields.Char(string='Shop ID')
    ship_to_id = fields.Char(string='Ship To ID')
    message = fields.Text(string='Logging')

    def create_feeds(self, sale_list):
        for sale in sale_list:
            try:
                feed = self.create_feed(sale)
                self += feed
            except Exception as e:
                continue
        return self

    def create_feed(self, sale):
        try:
            self.message = ''
            _logger.info('Start creating/updating order feeds: {}'.format(sale.get('ticketNumber')))
            vals = {
                'order_data': sale,
                'instance_id': self.env.context.get('instance_id').id,
                'name': sale.get('saleID'),
                'completed': sale.get('completed'),
                'sale_id': sale.get('saleID'),
                'reference_number': sale.get('referenceNumber'),
                'reference_number_source': sale.get('referenceNumberSource'),
                'ticket_number': sale.get('ticketNumber'),
                'total': sale.get('calcTotal'),
                'discount': sale.get('calcDiscount'),
                'tax_amount': sale.get('taxTotal'),
                'payment_amount': sale.get('calcPayments'),
                'tips': sale.get('calcTips'),
                'customer_id': sale.get('customerID'),
                'employee_id': sale.get('employeeID'),
                'shop_id': sale.get('shopID'),
                'ship_to_id': sale.get('shipToID')
            }
            customer_feed_id = self.env['lightspeed.customer.feeds'].create_feed(sale.get('Customer'))
            customer_feed_id.evaluate_feed()
            feed_id = self.search([('name', '=', sale.get('saleID'))])
            if feed_id:
                feed.write(vals)
            else:
                feed = self.create(vals)
            return feed
        except Exception as e:
            self.state = 'error'
            self.message = e
            _logger.info(e)
            raise ValidationError(e)

    def evaluate_feed(self):
        _logger.info(self)
        for feed in self:
            try:
                _logger.info('Start evaluating feeds for order: {}'.format(feed.ticket_number))
                feed.message = ''
                res_partner = self.env['res.partner'].search(
                    [('lightspeed_customer_id', '=', feed.lightspeed_customer_id)])
                _logger.info(vals)
                if res_partner:
                    res_partner.write(vals)
                else:
                    res_partner = self.env['res.partner'].create(vals)
                feed.state = 'done'
            except Exception as e:
                self.state = 'error'
                self.message = e
                _logger.info(e)
                raise ValidationError(e)


class OrderLineFeed(models.Model):
    _name = 'order.line.feed'
    _description = 'Order Line Feed'

    order_feed_id = fields.Many2one('order.feed', string='Order Feed ID')
    lightspeed_sale_line_id = fields.Char(string='Sale Line ID')
    unit_qty = fields.Integer(string='Unit Qty')
    unit_price = fields.Float(string='Unit Price')
    is_layaway = fields.Boolean(string='Is Layaway')
    is_workorder = fields.Boolean(string='is Workorder')
    is_specialorder = fields.Boolean(string='Is Special Order')
    total_amount = fields.Float(string='Cal Total Amount')
    subtotal_amount = fields.Float(string='Cal Subtotal Amount')
    tax1_amount = fields.Float(string='calcTax1')
    tax2_amount = fields.Float(string='calcTax2')

