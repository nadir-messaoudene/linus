# -*- coding: utf-8 -*-
{
    'name': "Odoo Shopify Connector",
    'summary': """Odoo Shopify Connector""",
    'description': """Odoo Shopify Connector""",
    'author': "Syncoria Inc",
    'website': "http://www.syncoria.com",
    'category': 'Uncategorized',
    'version': '15.5.0.0.0',
    'depends': ['base', 'mail', 'syncoria_base_marketplace', 'sale','sale_management', 'stock','sale_stock','delivery','product','website'],
    'images': [
        'static/description/banner.gif',
    ],
    'data': [
        'security/ir.model.access.csv',
        # Data
        'data/feed_actions.xml',
        'data/ir_cron_data.xml',
        'data/ir_sequence_data.xml',
        'data/product.xml',
        'data/res_partner.xml',
        'data/update_history.xml',
        # Views
        'wizard/create_variant_shopify.xml',
        'views/res_partner.xml',
        'views/res_config_settings.xml',
        'views/product_template.xml',
        'views/marketplace_instance.xml',
        'views/sale_order.xml',
        # 'views/account.xml',
        'views/stock.xml',
        'views/shopify_warehouse_views.xml',
        'views/shopify_fulfilment.xml',
        # Wizards
        'wizard/fetch_customers_wiz.xml',
        'wizard/fetch_orders_wiz.xml',
        'wizard/fetch_products_wiz.xml',
        'wizard/update_stock.xml',
        'wizard/customer_delete_wiz.xml',
        'wizard/fetch_warehouse_wiz_view.xml',
        
        ################################################
        #FEED
        'wizard/fetch_feed_products_wiz.xml',
        'wizard/fetch_feed_orders_wiz.xml',
        'wizard/fetch_feed_customers_wiz.xml',
        'views/feed_products.xml',
        'views/feed_orders.xml',
        'views/feed_customers.xml',
        'views/shopify_transactions.xml',
        'views/shopify_refunds.xml',
        ################################################
        'views/webhooks.xml',
        'views/webhooks_config.xml',
        # 'views/sync_history.xml',
        'views/marketplace_logging.xml',
        'views/shopify_dashnoard_view.xml',
        'views/update_stock_wizard.xml',
        'views/shopify_multi_store.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'syncoria_shopify/static/src/css/style.css',
        ],
    },
    'price': 500,
    'currency': 'USD',
    'license': 'OPL-1',
    'support': "support@syncoria.com"

}
