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
    instance_name = fields.Char(string='Instance Name', default='ResolvePay', required=True)
    instance_baseurl = fields.Char(string='Base URL', required=True)
    instance_secret_key = fields.Char(string='Secret Key', required=True)
    instance_merchant_id = fields.Char(string='Merchant ID', required=True)
    instance_version = fields.Char(string='Version')
    connect_state = fields.Selection([
        ('draft', 'Not Confirmed'),
        ('confirm', 'Confirmed')],
        default='draft', string='State')

    _sql_constraints = [
        ('instance_name_uniq', 'unique (instance_name)', 'Instance name must be unique.')
    ]

    def check_connect_access(self):
        complete_url = self.instance_baseurl if self.instance_baseurl.startswith("https://") else 'https://' + self.instance_baseurl
        complete_url += 'customers'
        data = None
        params = {'limit': 25, 'page': 1}
        headers = {'Content-Type': 'application/json'}
        _logger.info("Complete_url===>>>%s", complete_url)
        try:
            res = requests.request('GET', complete_url, headers=headers, data=data, params=params,  auth=HTTPBasicAuth(self.instance_merchant_id, self.instance_secret_key))
            if res.status_code != 200:
                _logger.warning(_("Error:" + str(res.error.get('message'))))
            else:
                self.connect_state = 'confirm'
        except Exception as e:
            _logger.info("Exception occured %s", e)
            raise UserError(_("Error Occured 5 %s") % e)

    def disconnect_access(self):
        self.connect_state = 'draft'

    # def _get_data(self, url, params=None, headers={}):
    #     headers.update({
    #         'Content-Type': 'application/json',
    #         'Authorization': 'Bearer %s' % (self.oauth_token),
    #     })
    #     params = params or dict()
    #     res = requests.get(
    #         url,
    #         params=params,
    #         headers=headers, verify=False
    #     )
    #     return res
    #
    # def _post_data(self, url, data=None, files=None, params={}, headers=None):
    #     if not headers or headers == None:
    #         headers = {
    #             'Content-Type': 'application/json',
    #             'Authorization': 'Bearer %s' % (self.oauth_token),
    #         }
    #     data = data or dict()
    #     if isinstance(data, dict):
    #         if data.get('username') and data.get('password'):
    #             data = '{"username": "%s", "password": "%s"}' % (data.get('username'), data.get('password'))
    #     if self.magento_auth_type == 'default':
    #         res = requests.post(
    #             url,
    #             data=data,
    #             params=params,
    #             files=files,
    #             headers=headers, verify=False,
    #         )
    #     return res