###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import logging
import json
import re
from odoo import _, http
from odoo.http import request
from werkzeug import urls, utils

_logger = logging.getLogger(__name__)


# if self.shopify_order_transactions_create:
#     topics += ['order_transactions/create']
# if self.shopify_orders_cancelled:
#     topics +=  ['orders/cancel']
# if self.shopify_orders_create:
#     topics +=  ['orders/create']
# if self.shopify_orders_delete:
#     topics +=  ['orders/delete']
# if self.shopify_orders_edited:
#     topics +=  ['orders/edited']
# if self.shopify_orders_fulfilled:
#     topics +=  ['orders/fulfilled']
# if self.shopify_orders_paid:
#     topics +=  ['orders/paid']
# if self.shopify_orders_partially_fulfilled:
#     topics +=  ['orders/partially_fulfilled']
# if self.shopify_orders_updated:
#     topics +=  ['orders/updated']
# class ShopifyControllers(http.Controller):
#     @http.route("/shopify/orders/", type="json", auth="public", csrf=False)
#     def shopify_orders(self, **kwargs):
#         _logger.info("shopify_orders")
#         _logger.info(request.httprequest.url)
#         data = request.jsonrequest
#         _logger.info("data===>>>%s", data)
#         res = {}
#         return res
#         # data===>>>
#         # data===>>>{'id': 4209435213875, 'admin_graphql_api_id': 'gid://shopify/Order/4209435213875', 'app_id': 1354745, 'browser_ip': None, 'buyer_accepts_marketing': False, 'cancel_reason': None, 'cancelled_at': None, 'cart_token': None, 'checkout_id': 24827239333939, 'checkout_token': 'a6eac79f98f26c43299f706b497f2d36', 'client_details': {'accept_language': None, 'browser_height': None, 'browser_ip': None, 'browser_width': None, 'session_hash': None, 'user_agent': None}, 'closed_at': None, 'confirmed': True, 'contact_email': None, 'created_at': '2022-04-01T03:13:13-07:00', 'currency': 'USD', 'current_subtotal_price': '1.00', 'current_subtotal_price_set': {'shop_money': {'amount': '1.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '1.00', 'currency_code': 'USD'}}, 'current_total_discounts': '0.00', 'current_total_discounts_set': {'shop_money': {'amount': '0.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '0.00', 'currency_code': 'USD'}}, 'current_total_duties_set': None, 'current_total_price': '1.00', 'current_total_price_set': {'shop_money': {'amount': '1.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '1.00', 'currency_code': 'USD'}}, 'current_total_tax': '0.00', 'current_total_tax_set': {'shop_money': {'amount': '0.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '0.00', 'currency_code': 'USD'}}, 'customer_locale': 'en', 'device_id': None, 'discount_codes': [], 'email': '', 'estimated_taxes': False, 'financial_status': 'paid', 'fulfillment_status': None, 'gateway': 'manual', 'landing_site': None, 'landing_site_ref': None, 'location_id': None, 'name': '#1024', 'note': None, 'note_attributes': [], 'number': 24, 'order_number': 1024, 'order_status_url': 'https://linus-sandbox.myshopify.com/56040161331/orders/a98abd390da584c608ab3bcb10ed6052/authenticate?key=894f8434e4daf81fd334cf053878d5e2', 'original_total_duties_set': None, 'payment_gateway_names': ['manual'], 'phone': None, 'presentment_currency': 'USD', 'processed_at': '2022-04-01T03:13:13-07:00', 'processing_method': 'manual', 'reference': None, 'referring_site': None, 'source_identifier': None, 'source_name': 'shopify_draft_order', 'source_url': None, 'subtotal_price': '1.00', 'subtotal_price_set': {'shop_money': {'amount': '1.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '1.00', 'currency_code': 'USD'}}, 'tags': '', 'tax_lines': [], 'taxes_included': False, 'test': False, 'token': 'a98abd390da584c608ab3bcb10ed6052', 'total_discounts': '0.00', 'total_discounts_set': {'shop_money': {'amount': '0.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '0.00', 'currency_code': 'USD'}}, 'total_line_items_price': '1.00', 'total_line_items_price_set': {'shop_money': {'amount': '1.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '1.00', 'currency_code': 'USD'}}, 'total_outstanding': '0.00', 'total_price': '1.00', 'total_price_set': {'shop_money': {'amount': '1.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '1.00', 'currency_code': 'USD'}}, 'total_price_usd': '1.00', 'total_shipping_price_set': {'shop_money': {'amount': '0.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '0.00', 'currency_code': 'USD'}}, 'total_tax': '0.00', 'total_tax_set': {'shop_money': {'amount': '0.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '0.00', 'currency_code': 'USD'}}, 'total_tip_received': '0.00', 'total_weight': 1000, 'updated_at': '2022-04-01T03:13:14-07:00', 'user_id': 73109372979, 'billing_address': {'first_name': 'Ariful', 'address1': '', 'phone': '', 'city': '', 'zip': '', 'province': 'Alabama', 'country': 'United States', 'last_name': 'Haque', 'address2': '', 'company': '', 'latitude': None, 'longitude': None, 'name': 'Ariful Haque', 'country_code': 'US', 'province_code': 'AL'}, 'customer': {'id': 5584934699059, 'email': None, 'accepts_marketing': False, 'created_at': '2022-04-01T03:12:35-07:00', 'updated_at': '2022-04-01T03:13:13-07:00', 'first_name': 'Ariful', 'last_name': 'Haque', 'orders_count': 1, 'state': 'disabled', 'total_spent': '1.00', 'last_order_id': 4209435213875, 'note': None, 'verified_email': True, 'multipass_identifier': None, 'tax_exempt': False, 'phone': None, 'tags': '', 'last_order_name': '#1024', 'currency': 'USD', 'accepts_marketing_updated_at': '2022-04-01T03:13:13-07:00', 'marketing_opt_in_level': None, 'tax_exemptions': [], 'sms_marketing_consent': None, 'admin_graphql_api_id': 'gid://shopify/Customer/5584934699059', 'default_address': {'id': 6895775744051, 'customer_id': 5584934699059, 'first_name': 'Ariful', 'last_name': 'Haque', 'company': '', 'address1': '', 'address2': '', 'city': '', 'province': 'Alabama', 'country': 'United States', 'zip': '', 'phone': '', 'name': 'Ariful Haque', 'province_code': 'AL', 'country_code': 'US', 'country_name': 'United States', 'default': True}}, 'discount_applications': [], 'fulfillments': [], 'line_items': [{'id': 10763478138931, 'admin_graphql_api_id': 'gid://shopify/LineItem/10763478138931', 'fulfillable_quantity': 1, 'fulfillment_service': 'manual', 'fulfillment_status': None, 'gift_card': False, 'grams': 1001, 'name': 'Baby Gang Onesie Organic - NATURAL / TURQUOISE PRINT / 6-12 MONTHS', 'origin_location': {'id': 3226243694643, 'country_code': 'US', 'province_code': 'CA', 'name': 'linus-sandbox', 'address1': '1901 Lincoln Blvd', 'address2': '', 'city': 'Venice', 'zip': '90291'}, 'price': '1.00', 'price_set': {'shop_money': {'amount': '1.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '1.00', 'currency_code': 'USD'}}, 'product_exists': True, 'product_id': 6684285861939, 'properties': [], 'quantity': 1, 'requires_shipping': True, 'sku': 'C/BOO106TQNAT6', 'taxable': True, 'title': 'Baby Gang Onesie Organic', 'total_discount': '0.00', 'total_discount_set': {'shop_money': {'amount': '0.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '0.00', 'currency_code': 'USD'}}, 'variant_id': 40410156990515, 'variant_inventory_management': 'shopify', 'variant_title': 'NATURAL / TURQUOISE PRINT / 6-12 MONTHS', 'vendor': 'Linus', 'tax_lines': [], 'duties': [], 'discount_allocations': []}], 'payment_terms': None, 'refunds': [], 'shipping_address': {'first_name': 'Ariful', 'address1': '', 'phone': '', 'city': '', 'zip': '', 'province': 'Alabama', 'country': 'United States', 'last_name': 'Haque', 'address2': '', 'company': '', 'latitude': None, 'longitude': None, 'name': 'Ariful Haque', 'country_code': 'US', 'province_code': 'AL'}, 'shipping_lines': []}
# data =
#  {'id': 4209435213875, 
# 'admin_graphql_api_id': 
# 'gid://shopify/Order/4209435213875', 
# 'app_id': 1354745, 'browser_ip': None,
#  'buyer_accepts_marketing': False, 'cancel_reason': None, 'cancelled_at': None, 'cart_token': None, 'checkout_id': 24827239333939, 'checkout_token': 'a6eac79f98f26c43299f706b497f2d36', 'client_details': {'accept_language': None, 'browser_height': None, 'browser_ip': None, 'browser_width': None, 'session_hash': None, 'user_agent': None}, 'closed_at': None, 'confirmed': True, 'contact_email': None, 'created_at': '2022-04-01T03:13:13-07:00', 'currency': 'USD', 'current_subtotal_price': '1.00', 'current_subtotal_price_set': {'shop_money': {'amount': '1.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '1.00', 'currency_code': 'USD'}}, 'current_total_discounts': '0.00', 'current_total_discounts_set': {'shop_money': {'amount': '0.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '0.00', 'currency_code': 'USD'}}, 'current_total_duties_set': None, 'current_total_price': '1.00', 'current_total_price_set': {'shop_money': {'amount': '1.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '1.00', 'currency_code': 'USD'}}, 'current_total_tax': '0.00', 'current_total_tax_set': {'shop_money': {'amount': '0.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '0.00', 'currency_code': 'USD'}}, 'customer_locale': 'en', 'device_id': None, 'discount_codes': [], 'email': '', 'estimated_taxes': False, 'financial_status': 'paid', 'fulfillment_status': None, 'gateway': 'manual', 'landing_site': None, 'landing_site_ref': None, 'location_id': None, 'name': '#1024', 'note': None, 'note_attributes': [], 'number': 24, 'order_number': 1024, 'order_status_url': 'https://linus-sandbox.myshopify.com/56040161331/orders/a98abd390da584c608ab3bcb10ed6052/authenticate?key=894f8434e4daf81fd334cf053878d5e2', 'original_total_duties_set': None, 'payment_gateway_names': ['manual'], 'phone': None, 'presentment_currency': 'USD', 'processed_at': '2022-04-01T03:13:13-07:00', 'processing_method': 'manual', 'reference': None, 'referring_site': None, 'source_identifier': None, 'source_name': 'shopify_draft_order', 'source_url': None, 'subtotal_price': '1.00', 'subtotal_price_set': {'shop_money': {'amount': '1.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '1.00', 'currency_code': 'USD'}}, 'tags': '', 'tax_lines': [], 'taxes_included': False, 'test': False, 'token': 'a98abd390da584c608ab3bcb10ed6052', 'total_discounts': '0.00', 'total_discounts_set': {'shop_money': {'amount': '0.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '0.00', 'currency_code': 'USD'}}, 'total_line_items_price': '1.00', 'total_line_items_price_set': {'shop_money': {'amount': '1.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '1.00', 'currency_code': 'USD'}}, 'total_outstanding': '0.00', 'total_price': '1.00', 'total_price_set': {'shop_money': {'amount': '1.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '1.00', 'currency_code': 'USD'}}, 'total_price_usd': '1.00', 'total_shipping_price_set': {'shop_money': {'amount': '0.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '0.00', 'currency_code': 'USD'}}, 'total_tax': '0.00', 'total_tax_set': {'shop_money': {'amount': '0.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '0.00', 'currency_code': 'USD'}}, 'total_tip_received': '0.00', 'total_weight': 1000, 'updated_at': '2022-04-01T03:13:14-07:00', 'user_id': 73109372979, 'billing_address': {'first_name': 'Ariful', 'address1': '', 'phone': '', 'city': '', 'zip': '', 'province': 'Alabama', 'country': 'United States', 'last_name': 'Haque', 'address2': '', 'company': '', 'latitude': None, 'longitude': None, 'name': 'Ariful Haque', 'country_code': 'US', 'province_code': 'AL'}, 'customer': {'id': 5584934699059, 'email': None, 'accepts_marketing': False, 'created_at': '2022-04-01T03:12:35-07:00', 'updated_at': '2022-04-01T03:13:13-07:00', 'first_name': 'Ariful', 'last_name': 'Haque', 'orders_count': 1, 'state': 'disabled', 'total_spent': '1.00', 'last_order_id': 4209435213875, 'note': None, 'verified_email': True, 'multipass_identifier': None, 'tax_exempt': False, 'phone': None, 'tags': '', 'last_order_name': '#1024', 'currency': 'USD', 'accepts_marketing_updated_at': '2022-04-01T03:13:13-07:00', 'marketing_opt_in_level': None, 'tax_exemptions': [], 'sms_marketing_consent': None, 'admin_graphql_api_id': 'gid://shopify/Customer/5584934699059', 'default_address': {'id': 6895775744051, 'customer_id': 5584934699059, 'first_name': 'Ariful', 'last_name': 'Haque', 'company': '', 'address1': '', 'address2': '', 'city': '', 'province': 'Alabama', 'country': 'United States', 'zip': '', 'phone': '', 'name': 'Ariful Haque', 'province_code': 'AL', 'country_code': 'US', 'country_name': 'United States', 'default': True}}, 'discount_applications': [], 'fulfillments': [], 'line_items': [{'id': 10763478138931, 'admin_graphql_api_id': 'gid://shopify/LineItem/10763478138931', 'fulfillable_quantity': 1, 'fulfillment_service': 'manual', 'fulfillment_status': None, 'gift_card': False, 'grams': 1001, 'name': 'Baby Gang Onesie Organic - NATURAL / TURQUOISE PRINT / 6-12 MONTHS', 'origin_location': {'id': 3226243694643, 'country_code': 'US', 'province_code': 'CA', 'name': 'linus-sandbox', 'address1': '1901 Lincoln Blvd', 'address2': '', 'city': 'Venice', 'zip': '90291'}, 'price': '1.00', 'price_set': {'shop_money': {'amount': '1.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '1.00', 'currency_code': 'USD'}}, 'product_exists': True, 'product_id': 6684285861939, 'properties': [], 'quantity': 1, 'requires_shipping': True, 'sku': 'C/BOO106TQNAT6', 'taxable': True, 'title': 'Baby Gang Onesie Organic', 'total_discount': '0.00', 'total_discount_set': {'shop_money': {'amount': '0.00', 'currency_code': 'USD'}, 'presentment_money': {'amount': '0.00', 'currency_code': 'USD'}}, 'variant_id': 40410156990515, 'variant_inventory_management': 'shopify', 'variant_title': 'NATURAL / TURQUOISE PRINT / 6-12 MONTHS', 'vendor': 'Linus', 'tax_lines': [], 'duties': [], 'discount_allocations': []}], 'payment_terms': None, 'refunds': [], 'shipping_address': {'first_name': 'Ariful', 'address1': '', 'phone': '', 'city': '', 'zip': '', 'province': 'Alabama', 'country': 'United States', 'last_name': 'Haque', 'address2': '', 'company': '', 'latitude': None, 'longitude': None, 'name': 'Ariful Haque', 'country_code': 'US', 'province_code': 'AL'}, 'shipping_lines': []}

# from pprint import pprint
# pprint(data)


def _get_instance_id():
    ICPSudo = request.env['ir.config_parameter'].sudo()
    try:
        marketplace_instance_id = ICPSudo.get_param(
            'syncoria_base_marketplace.marketplace_instance_id')
        marketplace_instance_id = [int(s) for s in re.findall(
            r'\b\d+\b', marketplace_instance_id)]
    except:
        marketplace_instance_id = False

    if marketplace_instance_id:
        marketplace_instance_id = request.env['marketplace.instance'].sudo().search(
            [('id', '=', marketplace_instance_id[0])])
    return marketplace_instance_id


def create_feed_orders(order_data):
    summary = ''
    error = ''
    feed_order_id = False
    try:
        marketplace_instance_id = False
        if order_data.get('app_id'):
            marketplace_instance_id = request.env['marketplace.instance'].sudo().search(
                [('marketplace_app_id', '=', order_data.get('app_id'))])
        if not marketplace_instance_id:
            marketplace_instance_id = _get_instance_id()


        domain = [('shopify_id', '=', order_data['id'])]
        feed_order_id = request.env['shopify.feed.orders'].sudo().search(domain, limit=1)
        if not feed_order_id:
            customer_name = order_data.get('customer',{}).get('first_name','') + ' ' + order_data.get('customer',{}).get('last_name','')
            feed_order_id = request.env['shopify.feed.orders'].sudo().create({
                'name': request.env['ir.sequence'].sudo().next_by_code('shopify.feed.orders'),
                'instance_id': marketplace_instance_id.id,
                'shopify_id': order_data['id'],
                'order_data': json.dumps(order_data),
                'state': 'draft',
                'shopify_webhook_call' : True,
                'shopify_app_id' : order_data.get('app_id'),
                'shopify_confirmed' : order_data.get('confirmed'),
                'shopify_contact_email' : order_data.get('contact_email'),
                'shopify_currency' : order_data.get('currency'),
                'shopify_customer_name' : customer_name,
                'shopify_customer_id' : order_data.get('customer',{}).get('id',''),
                'shopify_gateway' : order_data.get('gateway'),
                'shopify_order_number' : order_data.get('order_number'),
                'shopify_financial_status' : order_data.get('financial_status'),
                'shopify_fulfillment_status' : order_data.get('fulfillment_status'),
                'shopify_line_items' : len(order_data.get('line_items')),
                'shopify_user_id' : order_data.get('user_id'),
            })
            message = "Shopify Feed Order Created-{}".format(feed_order_id)
            summary += '\n' + message
            _logger.info("Shopify Feed Order Created-{}".format(feed_order_id))

        if feed_order_id:
            feed_order_id._cr.commit()
            feed_order_id.process_feed_order()
            

    except Exception as e:
        message = "Exception-{}".format(e.args)
        summary += '\n' + message
        error += '\n' + message
        _logger.warning("Exception-{}".format(e.args))
    
    if summary:
        log_id = request.env['marketplace.logging'].sudo().create({
            'name' : request.env['ir.sequence'].sudo().next_by_code('marketplace.logging'),
            'create_uid' : 1,
            'marketplace_type' : marketplace_instance_id.marketplace_instance_type,
            'shopify_instance_id' : marketplace_instance_id.id,
            'level' : 'info',
            'summary' : summary.replace('<br>','').replace('</br>','\n'),
            'error' : error.replace('<br>','').replace('</br>','\n'),
        })
        log_id._cr.commit()


    return feed_order_id


class ShopifyControllers(http.Controller):
    @http.route("/shopify/orders/", type="json", auth="public", csrf=False)
    def shopify_orders(self, **kwargs):
        feed_orders = request.env['shopify.feed.orders'].sudo()
        _logger.info("shopify_orders")
        _logger.info(request.httprequest.url)
        order_data = request.jsonrequest
        _logger.info("order_data===>>>%s", order_data)
        if order_data:
            feed_order_id = create_feed_orders(order_data)
            try:
                if feed_order_id:
                    feed_order_id.process_feed_order()
            except Exception as e:
                _logger.info("Feed Order Process Failed===>>>{}".format(e.args))

        return {}

    @http.route("/shopify/order_transactions/create/", type="json", auth="public", csrf=False)
    def shopify_order_transactions_create(self, **kwargs):
        _logger.info("shopify_order_transactions_create")
        _logger.info(request.httprequest.url)
        _logger.info("kwargs===>>>%s", kwargs)
        res = {}
        return res
