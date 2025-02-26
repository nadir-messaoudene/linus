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
from odoo.addons.website_sale.controllers.main import WebsiteSale
import random
import string
import re
import pprint
import urllib
import urllib.parse
_logger = logging.getLogger(__name__)


class ResolvepayController(WebsiteSale):

    # @http.route(['/resolvepay/success'], type='http', auth="public", website=True, sitemap=False, save_session=False)
    # def shop_payment_confirmation(self, **post):
    #     """ End of checkout process controller. Confirmation is basically seing
    #     the status of a sale.order. State at this point :
    #
    #      - should not have any context / session info: clean them
    #      - take a sale.order id, because we request a sale.order and are not
    #        session dependant anymore
    #     """
    #     sale_order_id = request.session.get('sale_last_order_id')
    #     if sale_order_id:
    #         order = request.env['sale.order'].sudo().browse(sale_order_id)
    #         if order.partner_id.available_credit < order.amount_total:
    #             tag_id = request.env['crm.tag'].sudo().search([('name', '=', 'B2B')])
    #             if tag_id:
    #                 order.tag_ids = [(4, tag_id.id)]
    #             tag_id = request.env['crm.tag'].sudo().search([('name', '=', 'Not Enough Credit')])
    #             if tag_id:
    #                 order.tag_ids = [(4, tag_id.id)]
    #             order.sudo().action_confirm()
    #             wiz = request.env['sale.advance.payment.inv'].sudo().with_context(active_ids=order.ids, open_invoices=True).create({})
    #             wiz.sudo().create_invoices()
    #             _logger.info("Creating Invoice for Sale Order-{}".format(order))
    #             move_id = request.env['account.move'].sudo().search(
    #                 [('invoice_origin', '=', order.name), ('move_type', "=", "out_invoice")])
    #             move_id.message_post(body=_(
    #                 "Customer does not have enough credit"))
    #         return request.render("syncoria_resolvepay.confirmation", {
    #             'order': order,
    #         })
    #     else:
    #         return request.redirect('/shop')

    # @http.route(['/resolvepay/cancel'], type='http', auth="public", website=True, save_session=False)
    # def resolvepay_after_success_cancel(self, **kw):
    #     try:
    #         request.website.sale_reset()
    #         return request.redirect('/shop')
    #     except Exception as e:
    #         _logger.warning("Exception-{}".format(e))

    @http.route(['/resolvepay/pre_confirmation'], type='http', auth="public", website=True, sitemap=False, save_session=False)
    def pre_confirmation(self, **post):
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            return request.render("syncoria_resolvepay.pre_confirmation", {
                'order': order,
            })
        else:
            return request.redirect('/shop')

    """ ROUTE FOR RESOLVE PAY WITHOUT ENOUGH CREDIT"""
    @http.route(['/shop/resolvepay_confirmation'], type='http', auth="public", website=True, sitemap=False)
    def shop_payment_rp_confirmation(self, **post):
        sale_order_id = request.session.get('sale_last_order_id')
        if sale_order_id:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            if order.state == 'draft':
                tag_id = request.env['crm.tag'].sudo().search([('name', '=', 'B2B')])
                if tag_id:
                    order.tag_ids = [(4, tag_id.id)]
                payment_term_id = request.env['account.payment.term'].sudo().search([('name', '=', 'NET 30')], limit=1)
                if payment_term_id:
                    order.payment_term_id = payment_term_id.id
                order.sudo().action_confirm()
                order.sudo()._send_order_confirmation_mail()
                tag_id = request.env['crm.tag'].sudo().search([('name', '=', 'Not Enough Credit')])
                if tag_id:
                    order.tag_ids = [(4, tag_id.id)]
            request.website.sale_reset()
            return request.render("syncoria_resolvepay.confirmation", {'order': order})
        else:
            return request.redirect('/shop')

    # @http.route('/shop/resolvepay/get_sale_order', type='json', auth="public", website=True, save_session=False)
    # def sale_order_info(self):
    #     order = request.website.sale_get_order()
    #     move_id = request.env['account.move'].sudo().search(
    #         [('invoice_origin', '=', order.name), ('move_type', "=", "out_invoice")])
    #     if move_id:
    #         return False
    #     customer_fname, customer_lname = self.name_split(order.partner_id.name)
    #     invoice_fname, invoice_lname = self.name_split(order.partner_invoice_id.name)
    #     item_list = []
    #
    #     if order.partner_id.resolvepay_customer_id and order.partner_id.available_credit < order.amount_total:
    #         return False
    #     else:
    #         tag_id = request.env['crm.tag'].sudo().search([('name', '=', 'B2B')])
    #         order.tag_ids = [(4, tag_id.id)]
    #         order.sudo().action_confirm()
    #         wiz = request.env['sale.advance.payment.inv'].sudo().with_context(
    #             active_ids=order.ids,
    #             open_invoices=True).create({})
    #         wiz.sudo().create_invoices()
    #         _logger.info("Creating Invoice for Sale Order-{}".format(order))
    #         move_id = request.env['account.move'].sudo().search(
    #             [('invoice_origin', '=', order.name), ('move_type', "=", "out_invoice")])
    #         if move_id and move_id.state != 'posted':
    #             move_id.sudo().action_post()
    #             for item in order.order_line:
    #                 item_list.append(dict(
    #                     name=item.name,
    #                     sku=item.product_id.default_code,
    #                     unit_price=item.price_unit,
    #                     quantity=item.product_uom_qty
    #                 ))
    #             return dict(
    #                 customer=dict(
    #                     first_name=customer_fname,
    #                     last_name=customer_lname,
    #                     phone=order.partner_id.phone,
    #                     email=order.partner_id.email
    #                 ),
    #                 shipping=dict(
    #                     name=order.partner_shipping_id.name,
    #                     phone=order.partner_shipping_id.phone,
    #                     address_line1=order.partner_shipping_id.street,
    #                     address_line2=order.partner_shipping_id.street2,
    #                     address_city=order.partner_shipping_id.city,
    #                     address_postal=order.partner_shipping_id.zip,
    #                     address_country=order.partner_shipping_id.country_id.code
    #                 ),
    #                 billing=dict(
    #                     first_name=invoice_fname,
    #                     last_name=invoice_lname,
    #                     phone=order.partner_invoice_id.phone
    #                 ),
    #                 item=item_list,
    #                 order_number=move_id.name,
    #                 shipping_amount=0,
    #                 tax_amount=order.amount_tax,
    #                 total_amount=order.amount_total
    #             )

    # def name_split(self, customer_name):
    #     fullname = customer_name.split(' ')
    #     name_length = len(fullname)
    #     lastname = fullname[-1]
    #     firstname = ' '.join(fullname[:name_length - 1])
    #     return firstname, lastname

    # @http.route(['/resolvepay/confirm'], type='http', auth="public", website=True, csrf=False, save_session=False)
    # def resolvepay_after_success(self, charge_id, **kw):
    #     try:
    #         order = request.website.sale_get_order()
    #         resolvepay_instance = request.env['resolvepay.instance'].sudo().search([('name', '=', 'ResolvePay')])
    #         check_charge_id_url = resolvepay_instance.instance_baseurl + 'charges/' + charge_id
    #         res = resolvepay_instance.get_data(check_charge_id_url)
    #         if res.get('data'):
    #             data = res.get('data')
    #             move_id = request.env['account.move'].sudo().search(
    #                 [('invoice_origin', '=', order.name), ('move_type', "=", "out_invoice")])
    #             if data.get('amount') == order.amount_total and data.get('order_number') == move_id.name:
    #                 move_id.resolvepay_charge_id = charge_id
    #                 url = resolvepay_instance.instance_baseurl + 'invoices'
    #                 res = resolvepay_instance.get_data(url, params={"filter[order_number][eq]": move_id.name})
    #                 if res.get('data'):
    #                     data = res.get('data')
    #                     _logger.info("Invoice data =====> %s", data)
    #                     invoice_resolvepay = data.get('results')
    #                     if data.get('count') == 1:
    #                         invoice_resolvepay = invoice_resolvepay[0]
    #                         move_id.resolvepay_invoice_id = invoice_resolvepay.get('id')
    #                         base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
    #                         invoice_url = base_url + '/my/invoices/' + str(move_id.id)
    #                         invoice_data = dict(
    #                             number=move_id.name,
    #                             order_number=order.name,
    #                             merchant_invoice_url=invoice_url
    #                         )
    #                         url = url + '/' + move_id.resolvepay_invoice_id
    #                         # resolvepay_instance.put_data(url=url, data=json.dumps(invoice_data))
    #                         request.website.sale_reset()
    #                         return request.redirect('/resolvepay/success')
    #                     elif data.get('count') > 1:
    #                         _logger.info("There are more than 1 invoice with the same name-{}".format(
    #                             invoice_resolvepay[0].get('order_number')))
    #                         isFound = False
    #                         for iv in invoice_resolvepay:
    #                             invoice_date = iv.get('created_at').split('T')[0]
    #                             if invoice_date == str(move_id.date):
    #                                 isFound = True
    #                                 move_id.resolvepay_invoice_id = iv.get('id')
    #                                 base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
    #                                 invoice_url = base_url + '/my/invoices/' + str(move_id.id)
    #                                 invoice_data = dict(
    #                                     number=move_id.name,
    #                                     order_number=order.name,
    #                                     merchant_invoice_url=invoice_url
    #                                 )
    #                                 url = url + '/' + move_id.resolvepay_invoice_id
    #                                 # resolvepay_instance.put_data(url=url, data=json.dumps(invoice_data))
    #                                 request.website.sale_reset()
    #                                 return request.redirect('/resolvepay/success')
    #                         if not isFound:
    #                             _logger.info("Can not find corresponding invoice from Resolve Pay")
    #                             request.website.sale_reset()
    #                             return request.redirect('/shop')
    #         else:
    #             _logger.warning("Exception: Invalid Charge Id:{}-{}".format(charge_id, order.name))
    #     except Exception as e:
    #         _logger.warning("Exception-{}".format(e))
    #         return request.redirect('/shop')

    @http.route('/shop/add_po_number', type='json', auth="public", website=True, save_session=False)
    def add_po_number(self, po=None):
        order = request.website.sale_get_order()
        if po and order:
            order.client_order_ref = po
        return True

    @http.route('/shop/validate_credit', type='json', auth="public", website=True, save_session=False)
    def validate_credit(self, partner=None, amount=None):
        partner_id = request.env['res.partner'].sudo().browse(partner)
        available_credit = 0
        if partner_id.resolvepay_customer_id:
            logging.info(partner_id.available_credit)
            logging.info('|')
            logging.info(amount)
            available_credit = partner_id.available_credit
        else:
            if partner_id.parent_id and partner_id.parent_id.resolvepay_customer_id:
                logging.info(partner_id.parent_id.available_credit)
                logging.info('|')
                logging.info(amount)
                available_credit = partner_id.parent_id.available_credit
        if available_credit > float(amount):
            return True
        else:
            return False

    @http.route('/shop/payment', type='http', auth='public', website=True, sitemap=False)
    def shop_payment(self, **post):
        """ Payment step. This page proposes several payment means based on available
        payment.acquirer. State at this point :

         - a draft sales order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.acquirer website but closed the tab without
           paying / canceling
        """
        order = request.website.sale_get_order()
        redirection = self.checkout_redirection(order) or self.checkout_check_address(order)
        if redirection:
            return redirection

        render_values = self._get_shop_payment_values(order, **post)
        render_values['only_services'] = order and order.only_services or False

        if render_values['errors']:
            render_values.pop('acquirers', '')
            render_values.pop('tokens', '')

        if 'acquirers' in render_values:
            payment_acquirers = render_values['acquirers']
            partner_id = render_values['partner']
            parent_id = partner_id.parent_id
            resolvepay_customer = False
            if partner_id:
                if partner_id.resolvepay_customer_id:
                    resolvepay_customer = True
                if parent_id:
                    if parent_id.resolvepay_customer_id:
                        resolvepay_customer = True
            if partner_id and not resolvepay_customer:
                payment_acquirers = payment_acquirers.filtered(lambda p: p.id != 18)
                render_values['acquirers'] = payment_acquirers

        return request.render("website_sale.payment", render_values)