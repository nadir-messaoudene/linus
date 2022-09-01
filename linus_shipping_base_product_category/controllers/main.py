# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.http import request
from odoo.addons.website_sale_delivery.controllers.main import WebsiteSaleDelivery
from odoo.exceptions import UserError


class WebsiteSaleDeliveryLinus(WebsiteSaleDelivery):

    def _get_shop_payment_values(self, order, **kwargs):
        values = super(WebsiteSaleDeliveryLinus, self)._get_shop_payment_values(order, **kwargs)
        if values.get('deliveries'):
            delivery_carriers = order._get_delivery_methods()
            values['deliveries'] = delivery_carriers.sudo()
        return values
