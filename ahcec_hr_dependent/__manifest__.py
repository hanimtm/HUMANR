# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

{
    'name': "HR Dependent",
    'summary': "HR Dependent",
    'description': """ """,
    'author': 'ahcec',
    'website': 'http://www.ahcec.com',
    'category': 'HR',
    'version': '1.0',
    'depends': ['ahcec_hr', 'res_documents'],
    'data': [
        'security/ir.model.access.csv',
        'views/ahcec_hr_dependent.xml',
        ],
    'demo': [],
    'images': [],
    "price": 30.0,
    "currency": "EUR",
    'installable': True,
    'auto_install': False,
}
