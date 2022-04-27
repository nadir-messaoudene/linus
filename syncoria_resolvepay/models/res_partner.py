from odoo import models, fields, api, _
import requests
from odoo.exceptions import UserError, ValidationError
from requests.auth import HTTPBasicAuth

import logging
_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = "res.partner"

    def create_customer_resolvepay(self):
        print('create_customer_resolvepay')