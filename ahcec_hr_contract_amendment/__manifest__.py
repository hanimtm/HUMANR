# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

{
    'name': "HR Contract Amendment",
    'summary': "HR Contract Amendment",
    'description': """
    """,
    'author': 'ahcec',
    'website': 'http://www.ahcec.com',
    'category': 'HR',
    'version': '1.0',
    'depends': ['hr', 'hr_contract', 'hr_payroll', 'ahcec_hr_payroll', 'ahcec_hr_leaves_management'],# 'ahcec_hr_grade','hr_warning'],
    'data': [
        'data/hr_payroll_data.xml',
        'security/ir.model.access.csv',
        'security/security.xml',
        'wizard/batch_payroll.xml',
        # 'wizard/leaves_adjust_view.xml',
        'views/amendment_view.xml',
        'menu.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}
