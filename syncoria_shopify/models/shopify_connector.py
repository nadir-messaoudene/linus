# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import logging
import json
import pprint
from odoo import models, fields, api, exceptions, _
_logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    _logger.info("Unable to import requests, please install it with pip install requests")


class ShopifyConnect(models.Model):
    _inherit = 'marketplace.connector'

    def shopify_api_call(self, **kwargs):
        """
        We will be running the api calls from here
        :param kwargs: dictionary with all the necessary parameters,
        such as url, header, data,request type, etc
        :return: response obtained for the api call
        """
        if kwargs.get('kwargs'):
            kwargs = kwargs.get('kwargs')
        if not kwargs:
            # no arguments passed
            return

        type = kwargs.get('type') or 'GET'
        complete_url = 'https://' + kwargs.get('url')
        _logger.info("complete_url===>>>%s", complete_url)
        headers = kwargs.get('headers')

        data = json.dumps(kwargs.get('data')) if kwargs.get('data') else None
        _logger.info("Request DATA==>>>" + pprint.pformat(data))

        try:
            res = requests.request(type, complete_url, headers=headers, data=data)
            if res.status_code != 200:
                _logger.warning(_("Error:" + str(res.text)))
            items = json.loads(res.text) if res.status_code == 200 else {'errors':res.text if res.text != '' else 'Error: Empty response from Shopify\nResponse Code: %s' %(res.status_code)}
            _logger.info("items==>>>" + pprint.pformat(items))
            return items
        except Exception as e:
            _logger.info("Exception occured %s", e)
            raise exceptions.UserError(_("Error Occured 5 %s") % e)
