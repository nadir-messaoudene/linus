###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import logging

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request
from werkzeug import urls, utils

_logger = logging.getLogger(__name__)


class ShopifyControllers(http.Controller):
    @http.route("/shopify/orders/", type="json", auth="public", csrf=False)
    def shopify_orders(self, **kwargs):
        _logger.info("shopify_orders")
        _logger.info(request.httprequest.url)
        _logger.info("kwargs===>>>%s", kwargs)
        res = {}
        return res