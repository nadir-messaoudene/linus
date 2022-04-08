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


    shopify_id = fields.Integer()
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
        print("shopify_webhook_request >>>>>>>>>>>>>>>")
        mkplc_id = self.marketplace_instance_id
        type_req = 'POST' if r_type == 'create' else 'PUT'
        version = mkplc_id.marketplace_api_version or '2021-04'
        url = 'https://' + mkplc_id.marketplace_host if 'https://' not in mkplc_id.marketplace_host or 'http://' not in mkplc_id.marketplace_host else mkplc_id.marketplace_host
        url += '/admin/api/%s/webhooks.json' % version

        headers = {
            # 'Content-Type': 'application/json',
            'X-Shopify-Access-Token': mkplc_id.marketplace_api_password
        }
        data = self.get_wb_data(r_type)
        response = requests.request(headers=headers,
                                    data=data,
                                    url=url,
                                    method=type_req)

        _logger.info("url===>>>%s", url)
        _logger.info("headers===>>>%s", headers)
        _logger.info("data===>>>%s", data)
        _logger.info("response===>>>%s", response)
        _logger.info("response===>>>%s", response.text)
        status_code = response.status_code
        res =  response.json()
        res['status_code'] = status_code
        return res

    def action_create_webhook(self):
        res = self.shopify_webhook_request('update')
        if res['status_code'] == 201:
            self.shopify_id = res.get('webhook', {}).get('id')
            msg = "Webhook Creation Successfull for %s,webhook id: %s" % (
                self.id, self.shopify_id)
            self.state = 'connected'
        else:
            msg = "Webhook Creation Failure for : %s\n%s", str(self.id), str(res)
        _logger.info("action_create_webhook===>>>%s", msg)
        self.message_post(body=msg)


    def action_update_webhook(self):
        res = self.shopify_webhook_request('create')
        if res.get('errors'):
            msg = "response Errors: \n%s", str(res.get('errors'))
            self.message_post(body=msg)
        else:
            msg = "Webhook Updated for %s,webhook id: %s" % (
                self.id, self.shopify_id)
        _logger.info("action_update_webhook===>>>%s", msg)
        self.message_post(body=msg)

    def get_wb_data(self, r_type):
        webhook = {
            'address': self.shopify_address,
            'topic': self.shopify_topic,
            'format': self.shopify_format,
        }
        webhook.update({'fields': self.shopify_fields or []})
        if r_type == 'update':
            webhook.update({'id': self.shopify_id})
        data = {'webhook': webhook}
        return data


class MarketplaceWebhooksConfig(models.Model):
    _inherit = 'marketplace.webhooks.config'

    #Topics
    # shopify_app_uninstalled = fields.Boolean(string="App uninstalled")
    # shopify_bulk_operations_finish = fields.Boolean(string="Bulk operations finish")
    # shopify_carts_create = fields.Boolean(string="Carts create")
    # shopify_carts_update = fields.Boolean(string="Carts update")
    # shopify_checkouts_create = fields.Boolean(string="Checkouts create")
    # shopify_checkouts_delete = fields.Boolean(string="Checkouts delete")
    # shopify_checkouts_update = fields.Boolean(string="Checkouts update")
    # shopify_collection_listings_add = fields.Boolean(string="Collection listings add")
    # shopify_collection_listings_remove = fields.Boolean(string="Collection listings remove")
    # shopify_collection_listings_update = fields.Boolean(string="Collection listings update")
    # shopify_collections_create = fields.Boolean(string="Collections create")
    # shopify_collections_delete = fields.Boolean(string="Collections delete")
    # shopify_collections_update = fields.Boolean(string="Collections update")
    # shopify_customer_groups_create = fields.Boolean(string="Customer groups create")
    # shopify_customer_groups_delete = fields.Boolean(string="Customer groups delete")
    # shopify_customer_groups_update = fields.Boolean(string="Customer groups update")
    # shopify_customer_payment_methods_create = fields.Boolean(string="Customer payment methods create")
    # shopify_customer_payment_methods_revoke = fields.Boolean(string="Customer payment methods revoke")
    # shopify_customer_payment_methods_update = fields.Boolean(string="Customer payment methods update")
    # shopify_customers_create = fields.Boolean(string="Customers create")
    # shopify_customers_delete = fields.Boolean(string="Customers delete")
    # shopify_customers_disable = fields.Boolean(string="Customers disable")
    # shopify_customers_enable = fields.Boolean(string="Customers enable")
    # shopify_customers_update = fields.Boolean(string="Customers update")
    # shopify_customers_marketing_consent_update = fields.Boolean(string="Customers marketing consent update")
    # shopify_disputes_create = fields.Boolean(string="Disputes create")
    # shopify_disputes_update = fields.Boolean(string="Disputes update")
    # shopify_domains_create = fields.Boolean(string="Domains create")
    # shopify_domains_destroy = fields.Boolean(string="Domains destroy")
    # shopify_domains_update = fields.Boolean(string="Domains update")
    # shopify_draft_orders_create = fields.Boolean(string="Draft orders create")
    # shopify_draft_orders_delete = fields.Boolean(string="Draft orders delete")
    # shopify_draft_orders_update = fields.Boolean(string="Draft orders update")
    # shopify_fulfillment_events_create = fields.Boolean(string="Fulfillment events create")
    # shopify_fulfillment_events_delete = fields.Boolean(string="Fulfillment events delete")
    # shopify_fulfillments_create = fields.Boolean(string="Fulfillments create")
    # shopify_fulfillments_update = fields.Boolean(string="Fulfillments update")
    # shopify_inventory_items_create = fields.Boolean(string="Inventory items create")
    # shopify_inventory_items_delete = fields.Boolean(string="Inventory items delete")
    # shopify_inventory_items_update = fields.Boolean(string="Inventory items update")
    # shopify_inventory_levels_connect = fields.Boolean(string="Inventory levels connect")
    # shopify_inventory_levels_disconnect = fields.Boolean(string="Inventory levels disconnect")
    # shopify_inventory_levels_update = fields.Boolean(string="Inventory levels update")
    # shopify_locales_create = fields.Boolean(string="Locales create")
    # shopify_locales_update = fields.Boolean(string="Locales update")
    # shopify_locations_create = fields.Boolean(string="Locations create")
    # shopify_locations_delete = fields.Boolean(string="Locations delete")
    # shopify_locations_update = fields.Boolean(string="Locations update")
    shopify_order_transactions_create = fields.Boolean(string="Order Transactions Create")
    shopify_orders_cancelled = fields.Boolean(string="Orders Cancelled")
    shopify_orders_create = fields.Boolean(string="Orders Create")
    shopify_orders_delete = fields.Boolean(string="Orders Delete")
    shopify_orders_edited = fields.Boolean(string="Orders Edited")
    shopify_orders_fulfilled = fields.Boolean(string="Orders Fulfilled")
    shopify_orders_paid = fields.Boolean(string="Orders Paid")
    shopify_orders_partially_fulfilled = fields.Boolean(string="Orders Partially Fulfilled")
    shopify_orders_updated = fields.Boolean(string="Orders Updated")
    # shopify_product_listings_add = fields.Boolean(string="Product listings add")
    # shopify_product_listings_remove = fields.Boolean(string="Product listings remove")
    # shopify_product_listings_update = fields.Boolean(string="Product listings update")
    # shopify_products_create = fields.Boolean(string="Products create")
    # shopify_products_delete = fields.Boolean(string="Products delete")
    # shopify_products_update = fields.Boolean(string="Products update")
    # shopify_profiles_create = fields.Boolean(string="Profiles create")
    # shopify_profiles_delete = fields.Boolean(string="Profiles delete")
    # shopify_profiles_update = fields.Boolean(string="Profiles update")
    # shopify_refunds_create = fields.Boolean(string="Refunds create")
    # shopify_scheduled_product_listings_add = fields.Boolean(string="Scheduled product listings add")
    # shopify_scheduled_product_listings_remove = fields.Boolean(string="Scheduled product listings remove")
    # shopify_scheduled_product_listings_update = fields.Boolean(string="Scheduled product listings update")
    # shopify_selling_plan_groups_create = fields.Boolean(string="Selling plan groups create")
    # shopify_selling_plan_groups_delete = fields.Boolean(string="Selling plan groups delete")
    # shopify_selling_plan_groups_update = fields.Boolean(string="Selling plan groups update")
    # shopify_shop_update = fields.Boolean(string="Shop update")
    # shopify_subscription_billing_attempts_challenged = fields.Boolean(string="Subscription billing attempts challenged")
    # shopify_subscription_billing_attempts_failure = fields.Boolean(string="Subscription billing attempts failure")
    # shopify_subscription_billing_attempts_success = fields.Boolean(string="Subscription billing attempts success")
    # shopify_subscription_contracts_create = fields.Boolean(string="Subscription contracts create")
    # shopify_subscription_contracts_update = fields.Boolean(string="Subscription contracts update")
    # shopify_tender_transactions_create = fields.Boolean(string="Tender transactions create")
    # shopify_themes_create = fields.Boolean(string="Themes create")
    # shopify_themes_delete = fields.Boolean(string="Themes delete")
    # shopify_themes_publish = fields.Boolean(string="Themes publish")
    # shopify_themes_update = fields.Boolean(string="Themes update")


    def shopify_activate_webhooks(self):
        print("shopify_activate_webhooks")
        marketplace_webhooks = self.env['marketplace.webhooks']
        topics = []
        if self.shopify_order_transactions_create:
            topics += ['order_transactions/create']
        if self.shopify_orders_cancelled:
            topics +=  ['orders/cancel']
        if self.shopify_orders_create:
            topics +=  ['orders/create']
        if self.shopify_orders_delete:
            topics +=  ['orders/delete']
        if self.shopify_orders_edited:
            topics +=  ['orders/edited']
        if self.shopify_orders_fulfilled:
            topics +=  ['orders/fulfilled']
        if self.shopify_orders_paid:
            topics +=  ['orders/paid']
        if self.shopify_orders_partially_fulfilled:
            topics +=  ['orders/partially_fulfilled']
        if self.shopify_orders_updated:
            topics +=  ['orders/updated']

        for topic in topics:
            domain = [('shopify_topic', '=', topic)]
            domain += [('marketplace_instance_id', '=', self.marketplace_instance_id.id)]
            topic_id = marketplace_webhooks.search(domain)
            _logger.info("topic_id ===>>>>{}".format(topic_id))

            if not topic_id:
                topic_id = marketplace_webhooks.create({
                    'name' : self.env['ir.sequence'].next_by_code('marketplace.webhooks') or 'New',
                    'company_id' : self.company_id.id,
                    'marketplace_instance_id' : self.marketplace_instance_id.id,
                    'marketplace_instance_type' : self.marketplace_instance_type,
                    'state' : 'draft',
                    'shopify_api_version' : self.marketplace_instance_id.marketplace_api_version or '2022-01',
                    'shopify_address' : '',
                    'shopify_topic' : topic,
                    'shopify_format' : 'json'
                })
                _logger.info("Webhook Created with Topic-{}".format(topic))


            if topic_id.state == 'connected':
                _logger.info("{} Webhook with Topic-{} is already connected".format(self, topic))

            if topic_id.state == 'draft':
                topic_id.action_create_webhook()


    def shopify_deactivate_webhooks(self):
        print("shopify_deactivate_webhooks")
        if self.shopify_id:
            mkplc_id = self.marketplace_instance_id
            type_req = 'DELETE'
            version = mkplc_id.marketplace_api_version or '2021-04'
            url = 'https://' + mkplc_id.marketplace_host if 'https://' not in mkplc_id.marketplace_host or 'http://' not in mkplc_id.marketplace_host else mkplc_id.marketplace_host
            url += '/admin/api/{}/webhooks/{}.json'.format(version,self.shopify_id)
            headers = {
                'X-Shopify-Access-Token': mkplc_id.marketplace_api_password
            }
            response = requests.request(headers=headers,
                                        url=url,
                                        method=type_req)

            _logger.info("url===>>>%s", url)
            _logger.info("headers===>>>%s", headers)
            _logger.info("response===>>>%s", response)
            _logger.info("response===>>>%s", response.text)
            if response.status_code == 200:
                _logger.info("Webhook Successfully Deleted")
        self.state = 'disconnected'


    
    