# -*- coding: utf-8 -*-
{
    'name': "Odoo Resolve Pay Connector",
    'summary': """Odoo Resolve Pay Connector""",
    'description': """Odoo Resolve Pay Connector""",
    'author': "Syncoria Inc",
    'website': "http://www.syncoria.com",
    'category': 'Uncategorized',
    'depends': ['base', 'account', 'website_sale_stock', 'website', 'web', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/resolvepay_view.xml',
        'views/res_partner.xml',
        'views/fetch_wizard_view.xml',
        'views/menu_item.xml',
        'views/account_move_view.xml',
        'views/direct_checkout_view.xml',
        'views/confirmation_view.xml'
    ],
    'assets': {
        'web.assets_frontend': [
            # 'https://app.resolvepay.com/js/resolve.js',
            'syncoria_resolvepay/static/js/resolvepay.js'
        ]
    },
    'license': 'OPL-1',
    'support': "support@syncoria.com"

}
