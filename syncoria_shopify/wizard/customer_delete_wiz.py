# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, exceptions, _
from odoo.http import request
import re
import logging

logger = logging.getLogger(__name__)


class CustomerFetchWizard(models.Model):
    _name = 'customer.delete.wizard'
    _description = 'Customer Delete Wizard'

    
    def delete_customer_shopify(self):
        """"""
    def delete_shopify_not(self):
        """"""