# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Middle East Human Resource Payroll",
    'summary': """ Middle East Human Resource Payroll """,
    'description': """ Middle East Human Resource Payroll """,
    'author': 'ahcec',
    'website': 'http://www.ahcec.com',
    'category': 'Human Resources',
    'version': '1.0',
    'sequence': 20,
    'depends': [
                'hr_expense_payment',
                'ahcec_hr_contract',
                ],
    # trevgdgre
    'data': [
        'security/ir.model.access.csv',
        'data/hr_payroll_data.xml',
        'security/ir_rule.xml',
        'views/other_hr_payslip.xml',
        'views/other_salary_rule.xml',
        'views/hr_payroll_view.xml',
        'views/type.xml',
        'views/hr_payslip_export_view.xml',
        'wizard/report_menu.xml',
        'wizard/company_payslip_report_view.xml',
        'menu.xml',
    ],
    # only loaded in demonstration mode
    'demo': ['demo/hr_employee_demo.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,
}
