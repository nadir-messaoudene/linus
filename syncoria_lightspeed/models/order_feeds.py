import json
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
from dateutil import parser

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
    sale_type = fields.Selection(
        string='Sale Type',
        selection=[('sale', 'Sale'),
                   ('refund', 'Refund'),
                   ('work_order', 'Work Order'),
                   ('layaway', 'Layaway'),
                   ('special', ' Special Order'),
                   ('deposit', 'Deposit'),
                   ('no_customer', 'No Customer')],
        default='sale'
    )
    completed = fields.Boolean(string='Completed')
    sale_id = fields.Char(string='Sale ID')
    reference_number = fields.Char(string='Reference Number')
    reference_number_source = fields.Char(string='Reference Number Source')
    ticket_number = fields.Char(string='Ticket Number')
    total = fields.Float(string='Total', digits=(12, 4))
    discount = fields.Float(string='Discount', digits=(12, 4))
    tax_amount = fields.Float(string='Tax Amount', digits=(12, 4))
    payment_amount = fields.Float(string='Payment Amount', digits=(12, 4))
    tips = fields.Float(string='Tips')
    customer_id = fields.Char(string='Customer ID')
    employee_id = fields.Char(string='Employee ID')
    shop_id = fields.Char(string='Shop ID')
    ship_to_id = fields.Char(string='Ship To ID')
    message = fields.Text(string='Logging')
    order_line_feed_ids = fields.One2many('order.line.feed', 'order_feed_id', string='Sale Lines')
    create_time = fields.Char(string='Create Time')
    tax_category_id = fields.Char(string='Tax Category ID')
    work_order_id = fields.Char(string='Work Order ID')
    is_shipped = fields.Boolean(string='Shipped?', default='True')

    _sql_constraints = [
        (
            'unique_order_feed_name',
            'UNIQUE(name)',
            'Name Must Be Unique',
        ),
    ]

    def create_feeds(self, sale_list):
        for sale in sale_list:
            try:
                feed = self.create_feed(sale)
                self += feed
            except Exception as e:
                _logger.info(e)
                continue
        return self

    def create_feed(self, sale):
        try:
            _logger.info('Start creating order feeds: {}'.format(sale.get('ticketNumber')))
            vals = {
                'name': sale.get('saleID'),
                'order_data': json.dumps(sale),
                'ticket_number': sale.get('ticketNumber'),
                'instance_id': self.env.context.get('instance_id').id,
                'state': 'draft'
            }
            feed_id = self.search([('name', '=', sale.get('saleID'))])
            if feed_id:
                feed_id.write(vals)
            else:
                feed_id = self.create(vals)
            return feed_id
        except Exception as e:
            _logger.info(e)
            raise ValidationError(e)

    def prepare_values(self, feed):
        sale = json.loads(feed.order_data)
        _logger.info('Start updating order feeds: {}'.format(sale.get('ticketNumber')))
        vals = {
            'completed': True if sale.get('completed') == 'true' else False,
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
            'ship_to_id': sale.get('shipToID'),
            'create_time': sale.get('createTime'),
            'tax_category_id': sale.get('taxCategoryID')
        }
        vals['order_line_feed_ids'] = feed.create_sale_line_feed(sale.get('SaleLines'))
        feed.write(vals)
        self.categorize_sale(feed)
        if feed.sale_type != 'no_customer':
            customer_feed_id = self.env['lightspeed.customer.feeds'].with_context(instance_id=feed.instance_id).create_feed(sale.get('Customer'))
            customer_feed_id.evaluate_feed()

    def categorize_sale(self, feed):
        if feed.total < 0:
            feed.sale_type = 'refund'
        elif feed.customer_id == '0':
            feed.sale_type = 'no_customer'
            if not feed.instance_id.fetch_no_customer_sale or not feed.instance_id.partner_id:
                raise ValidationError('This order does not have customer')
        elif not feed.order_line_feed_ids:
            feed.sale_type = 'deposit'
        # Work order can only be checked by SaleLines

    def evaluate_feed(self):
        _logger.info(self)
        for feed in self:
            try:
                feed.message = ''
                message = ''
                self.prepare_values(feed)
                sale = json.loads(feed.order_data)
                _logger.info('Start evaluating feeds for order: {}'.format(feed.ticket_number))
                if feed.sale_type == 'refund':
                    credit_note_id = self.create_credit_note(feed)
                elif feed.sale_type == 'deposit':
                    payment_id = self.create_deposit(feed)
                else:
                    vals = {}
                    res_partner = self.env['res.partner'].search([('lightspeed_customer_id', '=', feed.customer_id), ('type', '=', 'contact')], limit=1)
                    if feed.sale_type == 'no_customer' and feed.instance_id.partner_id:
                        res_partner = feed.instance_id.partner_id
                    if not res_partner:
                        raise ValidationError('Cannot find customerID: {}'.format(feed.customer_id))
                    if sale.get('shipToID') != '0':
                        if sale.get('ShipTo').get('shipped') == 'false':
                            feed.is_shipped = False
                        vals['partner_shipping_id'] = self.create_delivery_address(res_partner, sale.get('ShipTo'))
                    vals['partner_id'] = res_partner.id
                    vals['date_order'] = parser.parse(feed.create_time).replace(tzinfo=None)
                    order_line = feed.get_order_line_vals(feed.tax_category_id)
                    vals['order_line'] = order_line
                    vals['lightspeed_sale_id'] = feed.sale_id
                    lightspeed_shop = self.env['lightspeed.shop'].search([('shop_id', '=', feed.shop_id)])
                    vals['lightspeed_shop'] = lightspeed_shop.id
                    vals['warehouse_id'] = feed.instance_id.warehouse_id.id
                    vals['lightspeed_ticket_number'] = feed.ticket_number
                    tag_id = self.env['crm.tag'].search([('name', '=', 'Retail')], limit=1)
                    if tag_id:
                        vals['tag_ids'] = [(4, tag_id.id)]
                    match = self.env['sale.order'].search([('lightspeed_sale_id', '=', feed.sale_id)])
                    if match:
                        if match.state == 'draft':
                            match.write(vals)
                        else:
                            feed.message += 'Only Draft Order can be updated'
                    else:
                        match = self.env['sale.order'].create(vals)
                    payments = False
                    if sale.get('SalePayments'):
                        sale_payments = sale.get('SalePayments')
                        if type(sale_payments.get('SalePayment')) is dict:
                            payments = [sale_payments.get('SalePayment')]
                        else:
                            payments = sale_payments.get('SalePayment')
                    message = feed.set_order_state(match, feed.completed, feed.instance_id, payments, feed.is_shipped, vals.get('date_order'))
                feed.message += message
                feed.state = 'done'
            except Exception as e:
                feed.state = 'error'
                err_message = f'\nOrder Feed {feed.ticket_number}. Error: {str(e)}'
                feed.message += err_message
                _logger.info(err_message)
                continue

    def create_sale_line_feed(self, sale_line_data):
        lines = []
        lines += [(5, 0, 0)]
        if sale_line_data:
            if type(sale_line_data.get('SaleLine')) is dict:
                sale_lines = [sale_line_data.get('SaleLine')]
            else:
                sale_lines = sale_line_data.get('SaleLine')
            for sale_line in sale_lines:
                line = self.get_sale_line_feed_info(sale_line)
                if not line:
                    continue
                lines += [(0, 0, line)]
        _logger.info("Line Vals {}".format(lines))
        return lines

    def get_sale_line_feed_info(self, line):
        item = line.get('Item', False)
        if not item and line.get('SaleLineWorkOrder'):
            if line.get('SaleLineWorkOrder').get('workOrderType') == 'parent':
                self.sale_type = 'work_order'
                self.work_order_id = line.get('SaleLineWorkOrder').get('workOrderId')
                return False
        product_id = self.env['product.product'].search([('lightspeed_item_id', '=', item.get('itemID'))])
        if not product_id:
            product_feed = self.env['lightspeed.product.feeds'].create_feed(item)
            product_feed.evaluate_feed()
        line_dict = dict(
            lightspeed_sale_line_id=line.get('saleLineID'),
            lightspeed_parent_sale_line_id=line.get('parentSaleLineID'),
            unit_qty=line.get('unitQuantity'),
            unit_price=line.get('unitPrice'),
            is_layaway=True if line.get('isLayaway') == 'true' else False,
            is_workorder=True if line.get('isWorkorder') == 'true' else False,
            is_specialorder=True if line.get('isSpecialOrder') == 'true' else False,
            total_amount=line.get('calcTotal'),
            subtotal_amount=line.get('calcSubtotal'),
            tax1_amount=line.get('calcTax1'),
            tax2_amount=line.get('calcTax2'),
            lightspeed_item_id=line.get('itemID'),
            lightspeed_tax_class_id=line.get('taxClassID'),
            is_taxed=True if line.get('tax') == 'true' else False,
            tax1_rate=line.get('tax1Rate'),
            tax2_rate=line.get('tax2Rate'),
            discount_percent=line.get('discountPercent')
        )
        return line_dict

    def get_order_line_vals(self, tax_category_id):
        lines = []
        lines += [(5, 0, 0)]
        for line in self.order_line_feed_ids:
            product_id = self.env['product.product'].search([('lightspeed_item_id', '=', line.lightspeed_item_id)])
            if not product_id:
                raise ValidationError('Cannot find productID: {}'.format(line.lightspeed_item_id))
            vals = dict(
                price_unit=line.unit_price,
                product_id=product_id.id,
                product_uom_qty=line.unit_qty,
                lightspeed_sale_line_id=line.lightspeed_sale_line_id
            )
            if line.is_taxed:
                vals['tax_id'] = self.get_tax_id(tax_category_id, line.lightspeed_tax_class_id)
            if line.discount_percent > 0:
                vals['discount'] = line.discount_percent * 100
            lines += [(0, 0, vals)]
        return lines

    def get_tax_id(self, tax_category_id, tax_class_id):
        tax_category = self.instance_id.tax_ids.filtered(lambda tax: tax.lightspeed_tax_category_id == tax_category_id)
        if tax_category:
            tax_class = tax_category.tax_class_ids.filtered(lambda t: t.lightspeed_tax_class_id == tax_class_id)
            if tax_class:
                return tax_class.tax_id
            else:
                return tax_category.tax_id
        else:
            raise ValidationError('Cannot find Lightspeed Tax Class ID {} in Tax Category ID {}'.format(tax_class_id, tax_category_id))

    def create_delivery_address(self, partner_id, delivery_obj):
        try:
            _logger.info('Start creating/updating shipping address for customer: {}'.format(partner_id.name))
            contact = delivery_obj.get('Contact')
            addresses = contact.get('Addresses').get('ContactAddress')
            vals = {
                'name': delivery_obj.get('firstName') + " " + delivery_obj.get('lastName'),
                'lightspeed_ship_id': delivery_obj.get('shipToID'),
                'first_name': delivery_obj.get('firstName'),
                'last_name': delivery_obj.get('lastName'),
                'company': delivery_obj.get('company'),
                'street1': addresses.get('address1'),
                'street2': addresses.get('address2'),
                'city': addresses.get('city'),
                'state_name': addresses.get('state'),
                'state_code': addresses.get('stateCode'),
                'zip': addresses.get('zip'),
                'country': addresses.get('country'),
                'country_code': addresses.get('countryCode'),
            }
            if contact.get('Phones') != '':
                phones = contact.get('Phones').get('ContactPhone')
                if type(phones) is dict:
                    phones = [phones]
                for phone in phones:
                    if phone.get('useType') == 'Home':
                        vals['phone'] = phone.get('number')
                    if phone.get('useType') == 'Mobile':
                        vals['mobile'] = phone.get('number')
            if contact.get('Emails') != '':
                emails = contact.get('Emails').get('ContactEmail')
                if type(emails) is dict:
                    emails = [emails]
                for email in emails:
                    if email.get('useType') == 'Primary':
                        vals['email'] = email.get('address')
            if contact.get('Websites') != '':
                vals['website'] = contact.get('Websites').get('ContactWebsite').get('url')
            partner_dict = dict(
                type='delivery',
                parent_id=partner_id.id,
                lightspeed_ship_id=vals.get('lightspeed_ship_id'),
                name=vals.get('name'),
                street=vals.get('street1'),
                street2=vals.get('street2'),
                city=vals.get('city'),
                zip=vals.get('zip'),
                email=vals.get('email'),
                phone=vals.get('phone'),
                mobile=vals.get('mobile'),
                website=vals.get('website'),
            )
            country_id = self.env['res.country'].search([('code', '=', vals.get('country_code'))])
            if country_id:
                partner_dict['country_id'] = country_id.id
            state_id = self.env['res.country.state'].search(
                [('code', '=', vals.get('state_code')), ('country_id', '=', country_id.id)])
            if state_id:
                partner_dict['state_id'] = state_id.id
            delivery_obj = self.env['res.partner'].search([('lightspeed_ship_id', '=', delivery_obj.get('shipToID'))])
            if delivery_obj:
                delivery_obj.write(partner_dict)
            else:
                delivery_obj = self.env['res.partner'].create(partner_dict)
            return delivery_obj.id
        except Exception as e:
            _logger.info(e)
            raise ValidationError(e)

    def set_order_state(self, order_id, completed, instance_id, payments, shipped=True, order_date=False):
        status_message = "Order %s " % order_id.name
        if instance_id and completed:
            try:
                """ PROCESS SALE ORDER """
                if order_id.state == 'draft':
                    order_id.with_context({'date_order': order_date}).action_confirm()
                    # if order_date:
                    #     order_id.write()
                    status_message += '===> Confirmed'
                """ PROCESS INVOICE """
                if instance_id.create_invoice and not order_id.invoice_ids:
                    invoice_id = order_id._create_invoices()
                    date_invoice = order_id.date_order.date()
                    if date_invoice:
                        invoice_id.write({'invoice_date': date_invoice})
                    invoice_id.action_post()
                    status_message += '===> Invoice Created'
                """ PROCESS PAYMENT """
                if completed and instance_id.create_payment and payments and len(order_id.invoice_ids) == 1:
                    invoice_id = order_id.invoice_ids
                    if invoice_id.payment_state == 'not_paid':
                        for payment in payments:
                            if payment.get('archived') == 'true' or float(payment.get('amount')) == 0:
                                continue
                            payment_mapping = instance_id.payment_ids.filtered(lambda l: l.payment_type_id == payment.get('paymentTypeID'))
                            if payment_mapping:
                                register_wizard = self.env['account.payment.register'].with_context({
                                    'active_model': 'account.move',
                                    'active_ids': [invoice_id.id]
                                })
                                register_wizard_obj = register_wizard.create({
                                    'journal_id': payment_mapping.journal_id.id,
                                    'amount': payment.get('amount'),
                                    'payment_date': payment.get('createTime')[:10],
                                })
                                payment_res = register_wizard_obj.action_create_payments()
                            else:
                                raise ValidationError('There is no mapping for Payment Type {}'.format(payment.get('paymentTypeID')))
                        status_message += '===> Payments Created'
                """ PROCESS DELIVERY ORDER """
                if completed and instance_id.complete_delivery and shipped:
                    for picking in order_id.picking_ids:
                        if picking.state == 'draft':
                            picking.action_confirm()
                        if picking.state != 'assigned' and picking.state not in ['done', 'cancel']:
                            picking.action_assign()
                    for picking in order_id.picking_ids.filtered(
                            lambda pickingObj: pickingObj.picking_type_code in ['outgoing'] and pickingObj.state != 'done'):
                        backorder = False
                        context = dict(self._context or {})
                        context['active_id'] = picking.id
                        context['picking_id'] = picking.id
                        for move in picking.move_lines:
                            if move.move_line_ids:
                                for move_line in move.move_line_ids:
                                    move_line.qty_done = move_line.product_uom_qty
                            else:
                                move.quantity_done = move.product_uom_qty
                        if picking._check_backorder():
                            backorder = True
                            continue
                        if backorder:
                            backorder_obj = self.env['stock.backorder.confirmation'].create(
                                {'pick_ids': [(4, picking.id)]})
                            backorder_obj.with_context(context).process_cancel_backorder()
                        else:
                            picking.with_context(context)._action_done()
                        status_message += "===> Shipped. "
            except Exception as e:
                raise ValidationError(str(e))
        return status_message

    def create_deposit(self, feed):
        _logger.info('<--------- Start Creating Deposit ---------->')
        sale = json.loads(feed.order_data)
        payments = False
        payment_obj = self.env['account.payment'].search([('lightspeed_sale_id', '=', feed.sale_id)])
        if sale.get('SalePayments'):
            sale_payments = sale.get('SalePayments')
            if type(sale_payments.get('SalePayment')) is dict:
                payments = [sale_payments.get('SalePayment')]
            else:
                payments = sale_payments.get('SalePayment')
        if payments and not payment_obj:
            vals = self._prepare_payment_dict(payments, feed)
            if vals:
                payment_obj = self.env['account.payment'].create(vals)
                payment_obj.action_post()
        return payment_obj

    def _prepare_payment_dict(self, payments, feed):
        vals = {}
        for payment in payments:
            if payment.get('archived') == 'true' or float(payment.get('amount')) < 0:
                continue
            else:
                res_partner = self.env['res.partner'].search(
                    [('lightspeed_customer_id', '=', feed.customer_id), ('type', '=', 'contact')], limit=1)
                if not res_partner:
                    raise ValidationError('Cannot find customerID: {}'.format(feed.customer_id))
                payment_mapping = feed.instance_id.payment_ids.filtered(
                    lambda l: l.payment_type_id == payment.get('paymentTypeID'))
                vals = {
                    'amount': float(payment.get('amount')),
                    'date': payment.get('createTime')[:10],
                    'partner_type': 'customer',
                    'partner_id': res_partner.id,
                    'journal_id': payment_mapping.journal_id.id,
                    'payment_type': 'inbound',
                    'lightspeed_sale_id': feed.sale_id,
                    'lightspeed_ticket_number': feed.ticket_number,
                    'ref': feed.ticket_number
                }
        return vals

    def create_credit_note(self, feed):
        message = ""
        account_move = self.env['account.move'].sudo()
        refund_move_id = False
        sale_order = self.env['sale.order.line'].search([('lightspeed_sale_line_id', 'in', [feed.order_line_feed_ids.lightspeed_parent_sale_line_id])]).mapped('order_id')
        if len(sale_order) == 1:
            move_id = account_move.search([('invoice_origin', '=', sale_order.name), ('move_type', "=", "out_invoice")])
            refund_move_id = account_move.search([('invoice_origin', '=', sale_order.name), ('move_type', "=", "out_refund")])
            if move_id.payment_state in ['paid', 'in_payment'] and not refund_move_id:
                message += "\nCreating Credit Note for Sale Order-{}".format(sale_order.name)
                wizard_vals = {
                    'refund_method': 'refund',
                    'date_mode': 'custom',
                    'journal_id': move_id.journal_id.id,
                    'date': feed.create_time[:10],
                }
                reversal_wizard = self.env['account.move.reversal'].with_context(
                    active_model='account.move',
                    active_ids=move_id.ids).create(wizard_vals)
                reversal_wizard.sudo().reverse_moves()
                refund_move_id = account_move.search([('invoice_origin', '=', sale_order.name), ('move_type', "=", "out_refund")])
            if refund_move_id and refund_move_id.state == 'draft':
                refund_move_id.invoice_line_ids.with_context(check_move_validity=False).unlink()
                order_lines = self.env['sale.order.line'].search([('lightspeed_sale_line_id', 'in', [feed.order_line_feed_ids.lightspeed_parent_sale_line_id])])
                for line in order_lines:
                    vals = line._prepare_invoice_line()
                    vals['quantity'] = line.product_uom_qty
                    refund_move_id.invoice_line_ids = [(0, 0, vals)]
                refund_move_id.lightspeed_sale_id = feed.sale_id
                refund_move_id.lightspeed_ticket_number = feed.ticket_number
                refund_move_id.invoice_date = feed.create_time[:10]
                refund_move_id.action_post()
                message += "\nCredit Note-{} Posted for Sale Order-{}".format(refund_move_id.name, sale_order.name)
                feed.message = message
        elif len(sale_order) > 1:
            raise ValidationError('len(sale_order) > 1')
        else:
            raise ValidationError('Cannot find Sale Order for this refund')
        return refund_move_id


class OrderLineFeed(models.Model):
    _name = 'order.line.feed'
    _description = 'Order Line Feed'

    order_feed_id = fields.Many2one('lightspeed.order.feeds', string='Order Feed ID', ondelete='cascade')
    lightspeed_sale_line_id = fields.Char(string='Sale Line ID')
    lightspeed_parent_sale_line_id = fields.Char(string='parentSaleLineID')
    unit_qty = fields.Integer(string='Unit Qty')
    unit_price = fields.Float(string='Unit Price', digits=(12, 4))
    is_layaway = fields.Boolean(string='Is Layaway', default=False)
    is_workorder = fields.Boolean(string='is Workorder', default=False)
    is_specialorder = fields.Boolean(string='Is Special Order', default=False)
    total_amount = fields.Float(string='Cal Total Amount', digits=(12, 4))
    subtotal_amount = fields.Float(string='Cal Subtotal Amount', digits=(12, 4))
    tax1_amount = fields.Float(string='calcTax1', digits=(12, 4))
    tax1_rate = fields.Float(string='Tax1 Rate', digits=(12, 4))
    tax2_amount = fields.Float(string='calcTax2', digits=(12, 4))
    tax2_rate = fields.Float(string='Tax2 Rate', digits=(12, 4))
    lightspeed_item_id = fields.Char(string='Item ID')
    lightspeed_tax_class_id = fields.Char(string='taxClassID')
    is_taxed = fields.Boolean(string='Is Taxed?')
    discount_percent = fields.Float(string='Discount Percent', digits=(12, 4))
