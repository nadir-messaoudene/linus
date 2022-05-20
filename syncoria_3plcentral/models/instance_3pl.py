from odoo import models, fields
import requests
from requests.auth import HTTPBasicAuth

class Instance3PL(models.Model):
    _name = 'instance.3pl'
    _description = '3PL Instance'

    name = fields.Char(string='Instance Name', required=True)
    username = fields.Char(string='Username', required=True)
    password = fields.Char(string='Password', required=True)
    access_token = fields.Char(string='Access Token')

    _sql_constraints = [
        ('instance_name_uniq', 'unique (name)', 'Instance name must be unique.')
    ]

    def get_access_token(self):
        get_access_token_url = 'https://secure-wms.com/AuthServer/api/Token'
        headers = {'Content-Type': 'application/json'}
        response = requests.request('POST', get_access_token_url, auth=HTTPBasicAuth(self.username, self.password))
        print(response.status_code)
        # if result.status_code == 200: