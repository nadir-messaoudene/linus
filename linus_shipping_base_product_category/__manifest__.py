# -*- coding: utf-8 -*-
{
    'name': "Linus Bike Shipping Base Product Category",
    'summary': """Linus Bike Shipping Base Product Category""",
    'description': """Linus Bike Shipping Base Product Category""",
    'author': "Syncoria Inc",
    'website': "http://www.syncoria.com",
    'category': 'Uncategorized',
    'version': '1.0',
    'depends': ["delivery", "website_sale_delivery", "sale_management"],
    'images': [
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/delivery_view.xml',
        'views/delivery_grid_view.xml',
        'views/website_sale_delivery_templates.xml',
    ],
    'license': 'OPL-1',
    'support': "support@syncoria.com",
    'assets': {
        'web.assets_qweb': [
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
