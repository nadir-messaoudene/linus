# -*- coding: utf-8 -*-
{
    'name': "Odoo 3PL Central Connector",
    'summary': """Odoo 3PL Central Connector""",
    'description': """Odoo 3PL Central Connector""",
    'author': "Syncoria Inc",
    'website': "http://www.syncoria.com",
    'category': 'Stock',
    'depends': ['base', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/instance_3pl_view.xml',
        'views/res_partner.xml',
        'views/menu.xml',
        'views/refresh_access_token.xml',
        'views/stock_picking_view.xml',
        'views/product_product.xml'
    ],
    'license': 'OPL-1',
    'support': "support@syncoria.com"

}
