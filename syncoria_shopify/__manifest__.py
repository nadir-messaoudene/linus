# -*- coding: utf-8 -*-
{
    'name': "Odoo Shopify Connector",
    'summary': """Odoo Shopify Connector""",
    'description': """Odoo Shopify Connector""",
    'author': "Syncoria Inc",
    'website': "http://www.syncoria.com",
    'category': 'Uncategorized',
    'version': '15.2.0.0.0',
    'depends': ['base', 'mail', 'syncoria_base_marketplace', 'sale','sale_management', 'stock','sale_stock','delivery','product'],
    'images': [
        'static/description/banner.gif',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/res_partner.xml',
        'views/res_partner.xml',
        'views/res_config_settings.xml',
        'views/product_template.xml',
        'views/marketplace_instance.xml',
        'views/sale_order.xml',
        'views/account.xml',
        'views/stock.xml',
        'views/shopify_warehouse_views.xml',
        # Wizards
        'wizard/fetch_customers_wiz.xml',
        'wizard/fetch_orders_wiz.xml',
        'wizard/fetch_products_wiz.xml',
        'wizard/update_stock.xml',
        'wizard/customer_delete_wiz.xml',
        'wizard/fetch_warehouse_wiz_view.xml',
        ################################################
        'data/ir_sequence_data.xml',
        'wizard/fetch_feed_products_wiz.xml',
        'wizard/fetch_feed_orders_wiz.xml',
        'wizard/fetch_feed_customers_wiz.xml',
        #FEED
        'views/feed_products.xml',
        'views/feed_orders.xml',
        'views/feed_customers.xml',
        'views/shopify_transactions.xml',
        'views/shopify_refunds.xml',
        ################################################
        'views/webhooks.xml',
        # Data
        'data/ir_cron_data.xml',
        'data/update_history.xml',
        'data/product.xml',
    ],
    'price': 500,
    'currency': 'USD',
    'license': 'OPL-1',
    'support': "support@syncoria.com"

}
