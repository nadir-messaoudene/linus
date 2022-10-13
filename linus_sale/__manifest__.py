# -*- coding: utf-8 -*-
{
    'name': "Linus Bike Sale",
    'summary': """Linus Bike Sale""",
    'description': """Linus Bike Sale""",
    'author': "Syncoria Inc",
    'website': "http://www.syncoria.com",
    'category': 'Uncategorized',
    'version': '1.0',
    'depends': ['base', 'sale', 'sale_stock', 'web_domain_field', 'purchase'],
    'images': [
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_view.xml',
        'views/product_pricelist_views.xml',
        'views/purchase_order_view.xml'
    ],
    'license': 'OPL-1',
    'support': "support@syncoria.com",
}
