# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

{
    'name': "Employee Insurance & claim",
    'summary': """ Employee Insurance & claim details""",
    'description': """
         Employee Insurance & claim details
    """,
    'author': 'ahcec',
    'website': 'http://www.ahcec.com',
    'category': 'HR',
    'version': '1.0',
    'depends': ['ahcec_hr', 'hr', 'documents', 'account','ahcec_hr_dependent'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/product_data.xml',
        'data/email_template_data.xml',
        'data/cron.xml',
        'views/hr_employee_medical_view.xml',
        'views/menu.xml',
    ],
    'demo': [
        # 'demo/employee_demo.xml',
    ],
    "price": 80,
    "currency": "EUR",
    'images': [
        'static/description/main_screen.jpg'
    ],
    'installable': True,
    'auto_install': False,
}
