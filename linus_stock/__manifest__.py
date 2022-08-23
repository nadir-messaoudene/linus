# -*- coding: utf-8 -*-
{
    'name': "Linus Bike Stock",
    'summary': """Linus Bike Stock""",
    'description': """Linus Bike Stock""",
    'author': "Syncoria Inc",
    'website': "http://www.syncoria.com",
    'category': 'Uncategorized',
    'version': '1.0',
    'depends': ['base', 'stock', 'website_sale_stock'],
    'images': [
    ],
    'data': [
        'views/stock_picking_view.xml'
    ],
    'license': 'OPL-1',
    'support': "support@syncoria.com",
    'assets': {
        'web.assets_qweb': [
            'linus_stock/static/src/xml/**/*',
        ],
        'web.assets_backend': [
            'linus_stock/static/src/js/report_stock_forecasted.js',
        ],
    }
}
