{
    'name': 'Lightspeed Connector',
    'depends': ['base', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/fetch_wizard.xml',
        'views/feeds.xml',
        'views/lightspeed_view.xml',
    ],
    'application': True,
    'license': 'LGPL-3',
}