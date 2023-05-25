{
    'name': 'Lightspeed Connector',
    'depends': ['base', 'account', 'sale', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/fetch_wizard.xml',
        'views/sale.xml',
        'views/feeds.xml',
        'views/lightspeed_view.xml',
        'views/lightspeed_stock_wiz_view.xml',

    ],
    'application': True,
    'license': 'LGPL-3',
}