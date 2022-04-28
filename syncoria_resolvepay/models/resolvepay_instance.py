from odoo import models, fields, api, _
import requests
from odoo.exceptions import UserError, ValidationError
from requests.auth import HTTPBasicAuth

import logging
_logger = logging.getLogger(__name__)

class ResolvePay(models.Model):
    _name = 'resolvepay.instance'
    _description = 'Resolvepay Instance'

    # instance_api = fields.Char(string='API key')
    name = fields.Char(string='Instance Name', default='ResolvePay', required=True)
    instance_baseurl = fields.Char(string='Base URL', required=True)
    instance_secret_key = fields.Char(string='Secret Key', required=True)
    instance_merchant_id = fields.Char(string='Merchant ID', required=True)
    instance_version = fields.Char(string='Version')
    connect_state = fields.Selection([
        ('draft', 'Not Confirmed'),
        ('confirm', 'Confirmed')],
        default='draft', string='State')

    _sql_constraints = [
        ('instance_name_uniq', 'unique (name)', 'Instance name must be unique.')
    ]

    def check_connect_access(self):
        complete_url = self.instance_baseurl if self.instance_baseurl.startswith("https://") else 'https://' + self.instance_baseurl
        complete_url += 'customers'
        data = None
        params = {'limit': 25, 'page': 1}
        headers = {'Content-Type': 'application/json'}
        _logger.info("Complete_url===>>>%s", complete_url)
        res = self.get_data(complete_url, params=params, headers=headers)
        if res.get('data'):
            self.connect_state = 'confirm'
        else:
            raise ValidationError('Connect failed')

    def disconnect_access(self):
        self.connect_state = 'draft'

    def get_data(self, url, params=None, headers=None):
        if not headers or headers is None:
            headers = {
                'Content-Type': 'application/json'
            }
        _logger.info("Complete_url===>>>%s", url)
        try:
            res = dict()
            response = requests.request('GET', url, headers=headers, params=params, auth=HTTPBasicAuth(self.instance_merchant_id, self.instance_secret_key))
            if response.status_code != 200:
                content = response.content
                code = response.status_code
                _logger.warning(_("Error:" + str(content)))
                raise ValidationError('API returned %s response: %s' % (code, content))
            else:
                res['data'] = response.json()
        except Exception as e:
            _logger.info("Exception occured: %s", e)
            raise UserError(_("Error Occured: %s") % e)
        return res

    def post_data(self, url, data=None, headers=None):
        if not headers or headers is None:
            headers = {
                'Content-Type': 'application/json'
            }
        _logger.info("Complete_url===>>>%s", url)
        try:
            res = dict()
            response = requests.request('POST', url, headers=headers, data=data,  auth=HTTPBasicAuth(self.instance_merchant_id, self.instance_secret_key))
            if response.status_code != 200:
                content = response.content
                code = response.status_code
                _logger.warning(_("Error:" + str(content)))
                raise ValidationError('API returned %s response: %s' % (code, content))
            else:
                res['data'] = response.json()
        except Exception as e:
            _logger.info("Exception occured: %s", e)
            raise UserError(_("Error Occured: %s") % e)
        return res