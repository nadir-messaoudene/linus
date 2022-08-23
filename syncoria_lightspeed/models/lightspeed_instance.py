from email.policy import default
from odoo import api,fields, models
import requests
import json
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
    state = fields.Selection([('draft', 'Draft'), ('error', 'Error'), ('validate', 'Validate')], string='Status', default='draft')
    shop_ids = fields.One2many('lightspeed.shop', 'instance_id', string='Shop IDs')
    payment_ids = fields.One2many('lightspeed.payment', 'instance_id', string='Payment')

    def get_access_token(self):
        url = "https://cloud.lightspeedapp.com/oauth/access_token.php"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }
        res = self.post_request(url, payload)
        if res.get('access_token'):
            self.access_token = res.get('access_token')
            return True
        else:
            return False

    def check_connection(self):
        connect = self.get_access_token()
        if connect:
            self.state = 'validate'
            if self.account_id not in self.base_url:
                self.base_url = self.base_url + self.account_id + '/'
            self.fetch_shop()
            self.fetch_payment()

    def post_request(self, url, payload):
        try:
            response = requests.request("POST", url, data=payload)
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

    def get_request(self, url, query=None):
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

    def fetch_shop(self):
        res = self.get_request(self.base_url + 'Shop.json')
        if res:
            if self.shop_ids:
                self.shop_ids = [(5, 0, 0)]
            if type(res.get('Shop') is dict):
                shop = res.get('Shop')
                value = {'name': shop.get('name'),
                         'instance_id': self.id,
                         'shop_id': shop.get('shopID')
                         }
                self.env['lightspeed.shop'].create(value)
            else:
                for shop in res.get('Shop'):
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

    def fetch_orders(self, date_from, date_to):
        tz_offset = '-00:00'
        # if self.env.user and self.env.user.tz_offset:
        #     tz_offset = self.env.user.tz_offset
        date_from_convert = date_from.isoformat() + tz_offset
        date_to_convert = date_to.isoformat() + tz_offset
        res = self.get_request(self.base_url + 'Sale.json' + '?load_relations=["Customer","Customer.Contact","SaleLines"]&createTime=><,{},{}'.format(date_from_convert, date_to_convert))
        if res.get('Sale'):
            if type(res.get('Sale')) is dict:
                sale_list = [res.get('Sale')]
            else:
                sale_list = res.get('Sale')
            try:
                feeds = self.env['lightspeed.order.feeds'].with_context(instance_id=self).create_feeds(sale_list)
                feeds.evaluate_feed()
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
