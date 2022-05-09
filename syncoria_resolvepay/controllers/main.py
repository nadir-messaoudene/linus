from ast import Try
import logging
import pprint
import json
import requests
from werkzeug import urls, utils
from odoo import http, fields, tools, _
from odoo.service import common
from odoo.http import request
from odoo.addons.payment import utils as payment_utils
from odoo.exceptions import UserError, ValidationError

import random
import string
import re
import pprint
import urllib
import urllib.parse
_logger = logging.getLogger(__name__)

class ResolvepayController(http.Controller):

    @http.route(['/resolvepay/success'], type='http', auth="public", website=True, sitemap=False, save_session=False)
    def shop_payment_confirmation(self, **post):
        """ End of checkout process controller. Confirmation is basically seing
        the status of a sale.order. State at this point :

         - should not have any context / session info: clean them
         - take a sale.order id, because we request a sale.order and are not
           session dependant anymore
        """
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            return request.render("syncoria_resolvepay.confirmation", {
                'order': order,
            })
        else:
            return request.redirect('/shop')

    @http.route(['/resolvepay/cancel'], type='http', auth="public", website=True, save_session=False)
    def resolvepay_after_success(self, **kw):
        try:
            request.website.sale_reset()
            return request.redirect('/shop')
        except Exception as e:
            _logger.warning("Exception-{}".format(e))

    @http.route('/shop/resolvepay/get_sale_order', type='json', auth="public", website=True, save_session=False)
    def sale_order_info(self):
        print("sale_order_info")
        order = request.website.sale_get_order()
        print("sale_order ===>>>>", order)
        customer_fname, customer_lname = self.name_split(order.partner_id.name)
        invoice_fname, invoice_lname = self.name_split(order.partner_invoice_id.name)
        item_list = []
        for item in order.order_line:
            item_list.append(dict(
                name=item.name,
                sku=item.product_id.default_code,
                unit_price=item.price_unit,
                quantity=item.product_uom_qty
            ))
        return dict(
            customer=dict(
                first_name=customer_fname,
                last_name=customer_lname,
                phone=order.partner_id.phone,
                email=order.partner_id.email
            ),
            shipping=dict(
                name=order.partner_shipping_id.name,
                phone=order.partner_shipping_id.phone,
                address_line1=order.partner_shipping_id.street,
                address_line2=order.partner_shipping_id.street2,
                address_city=order.partner_shipping_id.city,
                address_postal=order.partner_shipping_id.zip,
                address_country=order.partner_shipping_id.country_id.code
            ),
            billing=dict(
                first_name=invoice_fname,
                last_name=invoice_lname,
                phone=order.partner_invoice_id.phone
            ),
            item=item_list,
            order_number=order.name,
            shipping_amount=0,
            tax_amount=order.amount_tax,
            total_amount=order.amount_total
        )

    def name_split(self, customer_name):
        fullname = customer_name.split(' ')
        name_length = len(fullname)
        lastname = fullname[-1]
        firstname = ' '.join(fullname[:name_length - 1])
        return firstname, lastname

    @http.route(['/resolvepay/confirm'], type='http', auth="public", website=True, save_session=False)
    def resolvepay_after_success(self, charge_id, **kw):
        try:
            print("resolvepay_after_success")
            order = request.website.sale_get_order()
            print("sale_order ===>>>>", order)
            order.sudo().action_confirm()
            _logger.info("Creating Invoice for Sale Order-{}".format(order))
            wiz = request.env['sale.advance.payment.inv'].sudo().with_context(
                active_ids=order.ids,
                open_invoices=True).create({})
            wiz.sudo().create_invoices()
            move_id = request.env['account.move'].sudo().search(
                [('invoice_origin', '=', order.name), ('move_type', "=", "out_invoice")])
            move_id.resolvepay_invoice_id = charge_id
            if move_id and move_id.state != 'posted':
                move_id.sudo().action_post()
                request.website.sale_reset()
                return request.redirect('/resolvepay/success')
        except Exception as e:
            _logger.warning("Exception-{}".format(e))


