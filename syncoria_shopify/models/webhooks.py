# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################


import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import requests
import json


FORMATS = [
    ('json', 'JSON'),
    ('xml', 'XML'),
]
TOPICS = [('app/uninstalled', 'app/uninstalled'), ('bulk_operations/finish', 'bulk_operations/finish'), ('carts/create', 'carts/create'), ('carts/update', 'carts/update'), ('checkouts/create', 'checkouts/create'), ('checkouts/delete', 'checkouts/delete'), ('checkouts/update', 'checkouts/update'), ('collection_listings/add', 'collection_listings/add'), ('collection_listings/remove', 'collection_listings/remove'), ('collection_listings/update', 'collection_listings/update'), ('collections/create', 'collections/create'), ('collections/delete', 'collections/delete'), ('collections/update', 'collections/update'), ('customer_groups/create', 'customer_groups/create'), ('customer_groups/delete', 'customer_groups/delete'), ('customer_groups/update', 'customer_groups/update'), ('customer_payment_methods/create', 'customer_payment_methods/create'), ('customer_payment_methods/revoke', 'customer_payment_methods/revoke'), ('customer_payment_methods/update', 'customer_payment_methods/update'), ('customers/create', 'customers/create'), ('customers/delete', 'customers/delete'), ('customers/disable', 'customers/disable'), ('customers/enable', 'customers/enable'), ('customers/update', 'customers/update'), ('customers_marketing_consent/update', 'customers_marketing_consent/update'), ('disputes/create', 'disputes/create'), ('disputes/update', 'disputes/update'), ('domains/create', 'domains/create'), ('domains/destroy', 'domains/destroy'), ('domains/update', 'domains/update'), ('draft_orders/create', 'draft_orders/create'), ('draft_orders/delete', 'draft_orders/delete'), ('draft_orders/update', 'draft_orders/update'), ('fulfillment_events/create', 'fulfillment_events/create'), ('fulfillment_events/delete', 'fulfillment_events/delete'), ('fulfillments/create', 'fulfillments/create'), ('fulfillments/update', 'fulfillments/update'), ('inventory_items/create', 'inventory_items/create'), ('inventory_items/delete', 'inventory_items/delete'), ('inventory_items/update', 'inventory_items/update'), ('inventory_levels/connect', 'inventory_levels/connect'), ('inventory_levels/disconnect', 'inventory_levels/disconnect'),
          ('inventory_levels/update', 'inventory_levels/update'), ('locales/create', 'locales/create'), ('locales/update', 'locales/update'), ('locations/create', 'locations/create'), ('locations/delete', 'locations/delete'), ('locations/update', 'locations/update'), ('order_transactions/create', 'order_transactions/create'), ('orders/cancelled', 'orders/cancelled'), ('orders/create', 'orders/create'), ('orders/delete', 'orders/delete'), ('orders/edited', 'orders/edited'), ('orders/fulfilled', 'orders/fulfilled'), ('orders/paid', 'orders/paid'), ('orders/partially_fulfilled', 'orders/partially_fulfilled'), ('orders/updated', 'orders/updated'), ('product_listings/add', 'product_listings/add'), ('product_listings/remove', 'product_listings/remove'), ('product_listings/update', 'product_listings/update'), ('products/create', 'products/create'), ('products/delete', 'products/delete'), ('products/update', 'products/update'), ('profiles/create', 'profiles/create'), ('profiles/delete', 'profiles/delete'), ('profiles/update', 'profiles/update'), ('refunds/create', 'refunds/create'), ('scheduled_product_listings/add', 'scheduled_product_listings/add'), ('scheduled_product_listings/remove', 'scheduled_product_listings/remove'), ('scheduled_product_listings/update', 'scheduled_product_listings/update'), ('selling_plan_groups/create', 'selling_plan_groups/create'), ('selling_plan_groups/delete', 'selling_plan_groups/delete'), ('selling_plan_groups/update', 'selling_plan_groups/update'), ('shop/update', 'shop/update'), ('subscription_billing_attempts/challenged', 'subscription_billing_attempts/challenged'), ('subscription_billing_attempts/failure', 'subscription_billing_attempts/failure'), ('subscription_billing_attempts/success', 'subscription_billing_attempts/success'), ('subscription_contracts/create', 'subscription_contracts/create'), ('subscription_contracts/update', 'subscription_contracts/update'), ('tender_transactions/create', 'tender_transactions/create'), ('themes/create', 'themes/create'), ('themes/delete', 'themes/delete'), ('themes/publish', 'themes/publish'), ('themes/update', 'themes/update')]


_logger = logging.getLogger(__name__)


class MarketplaceWebhooks(models.Model):
    _inherit = 'marketplace.webhooks'

    shopify_id = fields.Integer(
        string='Shopify Id',
    )
    shopify_api_version = fields.Char(
        related='marketplace_instance_id.marketplace_api_version',
        store=True
    )
    shopify_address = fields.Char("Address")
    shopify_topic = fields.Selection(selection=TOPICS, string="Topic")
    shopify_format = fields.Selection(
        selection=FORMATS, string="Format", default="json")
    shopify_fields = fields.Char("Fields")

    @api.onchange('shopify_format')
    def _onchange_field(self):
        if self.shopify_format != 'json':
            raise UserError(_("Only JSON is allowed for Shopify App."))

    def shopify_webhook_request(self, r_type):
        mkplc_id = self.marketplace_instance_id
        type_req = 'POST' if r_type == 'create' else 'PUT'
        version = mkplc_id.marketplace_api_version or '2021-04'
        url = 'https://' + mkplc_id.marketplace_host if 'https://' not in mkplc_id.marketplace_host or 'http://' not in mkplc_id.marketplace_host else mkplc_id.marketplace_host
        url += '/admin/api/%s/webhooks.json' % version

        headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Access-Token': mkplc_id.marketplace_api_password
        }
        data = self.get_wb_data(r_type)
        response = requests.request(headers=headers,
                                    data=data,
                                    url=url,
                                    method=type_req)
        _logger.info("headers===>>>%s", headers)
        _logger.info("data===>>>%s", data)
        _logger.info("response===>>>%s", response)
        status_code = response.status_code
        res =  response.json()
        res['status_code'] = status_code
        return response

    def action_create_webhook(self):
        res = self.shopify_webhook_request('create')
        if res['status_code'] == 201:
            self.shopify_id = res.get('webhook', {}).get('id')
            msg = "Webhook Creation Successfull for %s,webhook id: %s" % (
                self.id, self.shopify_id)
            _logger.info("msg===>>>%s", msg)
        else:
            msg = "Webhook Creation Failure for : %s\n%s", str(self.id), str(res.get('errors'))
            raise UserError(_(msg))




    def action_update_webhook(self):
        res = self.shopify_webhook_request('create')
        if res.get('errors'):
            msg = "response Errors: \n%s", str(res.get('errors'))
            raise UserError(_(msg))
        else:
            msg = "Webhook Updated for %s,webhook id: %s" % (
                self.id, self.shopify_id)
            _logger.info("msg===>>>%s", msg)

    def get_wb_data(self, r_type):
        webhook = {
            'address': self.shopify_address,
            'topic': self.shopify_topic,
            'format': self.shopify_format,
        }
        webhook.update({'fields': self.shopify_fields or []})
        webhook.update({'id': self.shopify_id}
                       ) if r_type == 'update' else webhook.update({})
        data = {'webhook': webhook}
        return data
