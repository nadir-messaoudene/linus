# -*- coding: utf-8 -*-
{
    'name': "Odoo Resolve Pay Connector",
    'summary': """Odoo Resolve Pay Connector""",
    'description': """Odoo Resolve Pay Connector""",
    'author': "Syncoria Inc",
    'website': "http://www.syncoria.com",
    'category': 'Uncategorized',
    'depends': ['base', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/resolvepay_view.xml',
        'views/res_partner.xml',
        'views/fetch_wizard_view.xml',
        'views/menu_item.xml',
        'views/account_move_view.xml'
    ],
    'license': 'OPL-1',
    'support': "support@syncoria.com"

}
