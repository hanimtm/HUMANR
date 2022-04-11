# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

{
    'name': "HR Grade",
    'summary': """ HR Grade""",
    'description': """
         HR Grade
    """,
    'author': 'ahcec',
    'website': 'http://www.ahcec.com',
    'category': 'HR',
    'version': '1.0',
    'depends': ['ahcec_hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_grade_view.xml',
    ],
    'price': 10,
    'currency': 'EUR',
    'demo': [],
    'images': [
        'static/description/main_screen.jpg'
    ],
    'installable': True,
    'auto_install': False,
}
