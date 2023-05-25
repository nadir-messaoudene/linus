from email.policy import default
from odoo import api,fields, models
import requests
import json
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import AccessError, UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)


class LightspeedInstance(models.Model):
    _name = 'lightspeed.instance'
    _description = 'Lightspeed Instance'

    name = fields.Char(required=True, string='Title')
    client_id = fields.Char(string='Client ID', required=True)
    client_secret = fields.Char(string='Client Secret', required=True)
    account_id = fields.Char(string='AccountID', required=True)
    refresh_token = fields.Char(string='Refresh Token', required=True)
    access_token = fields.Char(string='Access Token')
    base_url = fields.Char(string='Base URL', default='https://api.lightspeedapp.com/API/V3/Account/')
    state = fields.Selection([('draft', 'Draft'), ('error', 'Error'), ('connect', 'Connect'), ('validate', 'Validate')], string='Status', default='draft')
    shop_ids = fields.One2many('lightspeed.shop', 'instance_id', string='Shop IDs')
    payment_ids = fields.One2many('lightspeed.payment', 'instance_id', string='Payment')
    tax_ids = fields.One2many('lightspeed.tax.category', 'instance_id', string='Tax Category')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    create_invoice = fields.Boolean(string='Auto Create Invoice')
    create_payment = fields.Boolean(string='Auto Create Payment')
    complete_delivery = fields.Boolean(string='Auto Complete Delivery')
    fetch_no_customer_sale = fields.Boolean(string='Fetch No Customer Sale')
    partner_id = fields.Many2one('res.partner', string='Default Customer for Non-Customer Sale')

    def reset_to_draft(self):
        self.state = 'draft'

    def validate_config(self):
        payment_mapping = self.payment_ids.filtered(lambda l: not l.journal_id)
        if len(payment_mapping) > 0:
            payment_name = ''
            for payment in payment_mapping:
                payment_name += payment.name + ', '
            raise ValidationError('Please map [{}] payments.'.format(payment_name))
        tax_mapping = self.tax_ids.filtered(lambda l: not l.tax_id)
        if len(tax_mapping) > 0:
            tax_name = ''
            for tax in tax_mapping:
                tax_name += tax.name + ', '
            raise ValidationError('Please map [{}] taxes.'.format(tax_name))
        # else:
        #     tax_mapping_wrong = self.tax_ids.filtered(lambda l:  float_compare(l.tax1_rate * 100, l.tax_id.amount, precision_digits=4) != 0)
        #     msg = ''
        #     for tax in tax_mapping_wrong:
        #         msg += '{} has rate {}% but is mapped to Odoo rate {}%\n'.format(tax.name, tax.tax1_rate*100, tax.tax_id.amount)
        #     if tax_mapping_wrong:
        #         raise ValidationError('Rate of tax mapping does not match.\n'+msg)
            # else:
            #     for tax in self.tax_ids:
            #         tax_mapping_wrong = tax.tax_class_ids.filtered(
            #             lambda l: float_compare(l.tax1_rate * 100, l.tax_id.amount, precision_digits=4) != 0)
            #         if tax_mapping_wrong:
            #             raise ValidationError('Rate of tax class mapping does not match.')
        if not self.warehouse_id:
            raise ValidationError('Please select a warehouse to create sale order fetched from Lightspeed.')
        self.state = 'validate'

    def get_access_token(self):
        url = "https://cloud.lightspeedapp.com/oauth/access_token.php"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }
        res = self.post_request(url, payload, form_data=True)
        if res.get('access_token'):
            self.access_token = res.get('access_token')
            return True
        else:
            return False

    def check_connection(self):
        connect = self.get_access_token()
        if connect:
            self.state = 'connect'
            if self.account_id not in self.base_url:
                self.base_url = self.base_url + self.account_id + '/'
            self.fetch_shop()
            self.fetch_payment()
            self.fetch_tax_category()

    def post_request(self, url, payload, form_data=False):
        try:
            headers = {
                'Authorization': 'Bearer ' + self.access_token
            }
            if not form_data:
                payload = json.dumps(payload)
            response = requests.request("POST", url, data=payload, headers=headers)
            res = json.loads(response.text)
            if response.status_code == 200:
                _logger.info(res)
                return res
            else:
                _logger.info(res)
                self.state = 'error'
                raise ValidationError(res)
        except Exception as e:
            raise ValidationError(e)

    def put_request(self, url, payload):
        try:
            headers = {
                'Authorization': 'Bearer ' + self.access_token
            }
            response = requests.request("PUT", url, data=json.dumps(payload), headers=headers)
            res = json.loads(response.text)
            if response.status_code == 200:
                _logger.info(res)
                return res
            else:
                _logger.info(res)
                self.state = 'error'
                raise ValidationError(res)
        except Exception as e:
            raise ValidationError(e)

    def get_request(self, url):
        try:
            headers = {
                'Authorization': 'Bearer ' + self.access_token
            }
            response = requests.request("GET", url, headers=headers)
            res = json.loads(response.text)
            if response.status_code == 200:
                _logger.info(res)
                return res
            else:
                _logger.info(res)
                self.state = 'error'
                raise ValidationError(res)
        except Exception as e:
            raise ValidationError(e)

    def fetch_tax_category(self):
        res = self.get_request(self.base_url + 'TaxCategory.json?load_relations=all')
        if res:
            if self.tax_ids:
                self.tax_ids = [(5, 0, 0)]
            if type(res.get('TaxCategory')) is dict:
                tax_category_list = [res.get('TaxCategory')]
            else:
                tax_category_list = res.get('TaxCategory')
            for tax in tax_category_list:
                value = {
                    'name': tax.get('tax1Name'),
                    'instance_id': self.id,
                    'lightspeed_tax_category_id': tax.get('taxCategoryID'),
                    'is_tax_inclusive': True if tax.get('isTaxInclusive') == 'true' else False,
                    'tax1_name': tax.get('tax1Name'),
                    'tax2_name': tax.get('tax2Name'),
                    'tax1_rate': tax.get('tax1Rate'),
                    'tax2_rate': tax.get('tax2Rate')
                }
                tax_class_ids = []
                if tax.get('TaxCategoryClasses'):
                    tax_category_classes = tax.get('TaxCategoryClasses')
                    if type(tax_category_classes.get('TaxCategoryClass')) is dict:
                        tax_category_class_list = [tax_category_classes.get('TaxCategoryClass')]
                    else:
                        tax_category_class_list = tax_category_classes.get('TaxCategoryClass')
                    for category_class in tax_category_class_list:
                        line = dict(
                            name=category_class.get('TaxClass', {}).get('name'),
                            lightspeed_tax_class_id=category_class.get('taxClassID'),
                            tax1_rate=category_class.get('tax1Rate'),
                            tax2_rate=category_class.get('tax2Rate'),
                        )
                        tax_class_ids += [(0, 0, line)]
                        value['tax_class_ids'] = tax_class_ids
                self.env['lightspeed.tax.category'].create(value)

    def fetch_shop(self):
        res = self.get_request(self.base_url + 'Shop.json')
        if res:
            if self.shop_ids:
                self.shop_ids = [(5, 0, 0)]
            if type(res.get('Shop')) is dict:
                shop_list = [res.get('Shop')]
            else:
                shop_list = res.get('Shop')
            for shop in shop_list:
                value = {'name': shop.get('name'),
                         'instance_id': self.id,
                         'shop_id': shop.get('shopID')
                         }
                self.env['lightspeed.shop'].create(value)

    def fetch_payment(self):
        res = self.get_request(self.base_url + 'PaymentType.json')
        if res:
            if self.payment_ids:
                self.payment_ids = [(5, 0, 0)]
            for payment in res.get('PaymentType'):
                value = {'name': payment.get('name'),
                         'instance_id': self.id,
                         'payment_type_id': payment.get('paymentTypeID')
                         }
                self.env['lightspeed.payment'].create(value)

    def fetch_orders(self, kwargs):
        tz_offset = '-00:00'
        # if self.env.user and self.env.user.tz_offset:
        #     tz_offset = self.env.user.tz_offset
        load_relations = '?load_relations=["Customer","Customer.Contact","SaleLines","SaleLines.Item","ShipTo","ShipTo.Contact","SalePayments"]'
        url = 'Sale.json'
        time_range = ''
        completed = ''
        ticket_number = ''
        if kwargs.get('date_to') and kwargs.get('date_from'):
            date_to = kwargs.get('date_to')
            date_from = kwargs.get('date_from')
            date_from_convert = date_from.isoformat() + tz_offset
            date_to_convert = date_to.isoformat() + tz_offset
            time_range = '&timeStamp=><,{},{}'.format(date_from_convert, date_to_convert)
            if kwargs.get('completed'):
                completed = '&completed=true'
        elif kwargs.get('id_to_fetch'):
            id_to_fetch = kwargs.get('id_to_fetch')
            url = 'Sale/{}.json'.format(id_to_fetch)
        elif kwargs.get('ticket_number'):
            ticket_number = '&ticketNumber={}'.format(kwargs.get('ticket_number'))
        full_url = self.base_url + url + load_relations + time_range + completed + ticket_number
        res = self.get_request(full_url)
        sale_list = []
        if res.get('Sale'):
            if type(res.get('Sale')) is dict:
                sale_list += [res.get('Sale')]
            else:
                sale_list += res.get('Sale')
            while res.get('@attributes').get('next'):
                res = self.get_request(res.get('@attributes').get('next'))
                if res.get('Sale'):
                    if type(res.get('Sale')) is dict:
                        sale_list += [res.get('Sale')]
                    else:
                        sale_list += res.get('Sale')
            try:
                feeds = self.env['lightspeed.order.feeds'].with_context(instance_id=self).create_feeds(sale_list)
                feeds.evaluate_feed()
                # return {
                #     'name': 'Lightspeed Orders',
                #     'type': 'ir.actions.act_window',
                #     'view_type': 'form',
                #     'view_mode': 'tree,form',
                #     'res_model': 'sale.order',
                #     'view_id': False,
                #     'domain': [('lightspeed_sale_id', '!=', '')],
                #     'target': 'current',
                # }
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload'
                }
            except Exception as e:
                _logger.info(e)
                raise ValidationError(e)

    def fetch_products(self, kwargs):
        tz_offset = '-00:00'
        url = 'Item.json'
        time_range = ''
        load_relations = '?load_relations=["Category"]'
        if kwargs.get('date_to') and kwargs.get('date_from'):
            date_to = kwargs.get('date_to')
            date_from = kwargs.get('date_from')
            date_from_convert = date_from.isoformat() + tz_offset
            date_to_convert = date_to.isoformat() + tz_offset
            time_range = '&createTime=><,{},{}'.format(date_from_convert, date_to_convert)
        elif kwargs.get('id_to_fetch'):
            id_to_fetch = kwargs.get('id_to_fetch')
            url = 'Item/{}.json'.format(id_to_fetch)
        res = self.get_request(self.base_url + url + load_relations + time_range)
        if res.get('Item'):
            if type(res.get('Item')) is dict:
                item_list = [res.get('Item')]
            else:
                item_list = res.get('Item')
            try:
                feeds = self.env['lightspeed.product.feeds'].with_context(instance_id=self).create_feeds(item_list)
                feeds.with_context(fetch_prod=True).evaluate_feed()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload'
                }
            except Exception as e:
                _logger.info(e)
                raise ValidationError(e)

    def fetch_customers(self):
        res = self.get_request(self.base_url + 'Customer.json' + '?load_relations=["Contact"]')
        if res.get('Customer'):
            if type(res.get('Customer')) is dict:
                customer_list = [res.get('Customer')]
            else:
                customer_list = res.get('Customer')
            try:
                feeds = self.env['lightspeed.customer.feeds'].with_context(instance_id=self).create_feeds(customer_list)
                feeds.evaluate_feed()
                _logger.info('Import Orders: Done')
                return {
                    'name': 'Lightspeed Customers',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'res.partner',
                    'view_id': False,
                    'domain': [('lightspeed_customer_id', '!=', '')],
                    'target': 'current',
                }
            except Exception as e:
                _logger.info(e)
                raise ValidationError(e)


class LightspeedShop(models.Model):
    _name = 'lightspeed.shop'
    _description = 'Lightspeed Shop'

    name = fields.Char(required=True, string='Name')
    instance_id = fields.Many2one(required=True, string='Lightspeed Instance', comodel_name='lightspeed.instance', ondelete='cascade')
    shop_id = fields.Char(required=True, string='Shop ID')


class LightspeedPayment(models.Model):
    _name = 'lightspeed.payment'
    _description = 'Lightspeed Payment'

    name = fields.Char(required=True, string='Name')
    instance_id = fields.Many2one(required=True, string='Lightspeed Instance', comodel_name='lightspeed.instance', ondelete='cascade')
    payment_type_id = fields.Char(required=True, string='Payment Type ID')
    journal_id = fields.Many2one('account.journal', 'Odoo Journal')


class LightspeedTaxCategory(models.Model):
    _name = 'lightspeed.tax.category'
    _description = 'Lightspeed Tax Category'

    name = fields.Char(string='Name')
    instance_id = fields.Many2one(required=True, string='Lightspeed Instance', comodel_name='lightspeed.instance', ondelete='cascade')
    lightspeed_tax_category_id = fields.Char(string='Lightspeed taxCategoryID')
    is_tax_inclusive = fields.Boolean(string='isTaxInclusive')
    tax1_name = fields.Char(string='Tax1 Name')
    tax2_name = fields.Char(string='Tax2 Name')
    tax1_rate = fields.Float(string='Tax1 Rate', digits=(12, 4))
    tax2_rate = fields.Float(string='Tax2 Rate', digits=(12, 4))
    tax_id = fields.Many2one('account.tax', string='Tax Mapping')
    tax_class_ids = fields.One2many('lightspeed.tax.category.class', 'tax_category_id', string='Tax Category Class')


class LightspeedTaxCategoryClass(models.Model):
    _name = 'lightspeed.tax.category.class'
    _description = 'Lightspeed Tax Category Class'

    name = fields.Char(string='Name')
    tax_category_id = fields.Many2one(required=True, string='Tax Category', comodel_name='lightspeed.tax.category', ondelete='cascade')
    lightspeed_tax_class_id = fields.Char(string='Tax Class ID')
    tax1_rate = fields.Float(string='Tax1 Rate', digits=(12, 4))
    tax2_rate = fields.Float(string='Tax2 Rate', digits=(12, 4))
    tax_id = fields.Many2one('account.tax', string='Tax Mapping')
