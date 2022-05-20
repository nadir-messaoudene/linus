from odoo import models, fields
import requests, json
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

    def upsert_access_token(self):
        get_access_token_url = 'https://secure-wms.com/AuthServer/api/Token'
        payload = json.dumps({
            "grant_type": "client_credentials",
            })
        headers = {
            'Host': 'secure-wms.com',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip,deflate,sdch',
            'Accept-Language': 'en-US,en;q=0.8'
            }

        response = requests.request("POST", get_access_token_url, headers=headers, auth=HTTPBasicAuth(self.username, self.password), data=payload)
        if response.status_code == 200:
            response = json.loads(response.text)
            self.access_token = response.get('access_token')
            
    def refresh_access_token(self):
        to_refresh = self.env['instance.3pl'].search([])
        if not to_refresh:
            return
        for instance in to_refresh:
            instance.upsert_access_token()