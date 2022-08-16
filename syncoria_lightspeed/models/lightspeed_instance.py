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
    state = fields.Selection([('draft', 'Draft'), ('error', 'Error'), ('validate', 'Validate')], string='Status', default='draft')

    def check_connection(self):
        url = "https://cloud.lightspeedapp.com/oauth/access_token.php"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token"
        }
        try:
            response = requests.request("POST", url, data=payload)
            res = json.loads(response.text)
            if response.status_code == 200:
                logging.info(res)
                if res.get('access_token'):
                    self.access_token = res.get('access_token')
                    self.state = 'validate'
            else:
                logging.info(res)
                self.state = 'error'
                raise ValidationError(res)
        except Exception as e:
            raise ValidationError(e)
