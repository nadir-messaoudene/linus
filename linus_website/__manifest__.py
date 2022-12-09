# -*- coding: utf-8 -*-
{
    'name': "Linus B2B Website",
    'summary': """Linus B2B Website""",
    'description': """Linus B2B Website""",
    'author': "Syncoria Inc",
    'website': "http://www.syncoria.com",
    'category': 'Uncategorized',
    'version': '1.0',
    'depends': ['base', 'website', 'sale', 'account', 'payment_authorize', 'website_sale', 'website_sale_stock'],
    'images': [
    ],
    'data': [
        'views/portal_templates.xml',
        'views/product.xml',
    ],
    'license': 'OPL-1',
    'support': "support@syncoria.com",
    'assets': {
		'web.assets_frontend': [
             'linus_website/static/src/js/variant_mixin.js',
             'linus_website/static/src/scss/style.scss',
             'https://fonts.googleapis.com/css2?family=Open+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,300;1,400;1,500;1,600;1,700;1,800&display=swap',
        ]
    }
}
