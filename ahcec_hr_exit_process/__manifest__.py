# -*- coding: utf-8 -*-

{
    'name': 'HR Exit Process Management',
    'version': '1.1.8',
    'category': 'Human Resources',
    'summary': 'Employee Out/Exit/Termination Process Management',
    'description': """
        Employee Exit process:
            ---> Configure CheckLists
            ---> Employee Exit Request
            ---> Employee Exit Checklists
            ---> Print Employee Exit Report 
            """,
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'depends': ['hr', 'hr_contract', 'survey', 'calendar'],
    'data': [
        'security/hr_exit_security.xml',
        'security/ir.model.access.csv',
        'views/hr_exit_view.xml',
        'report/hr_exit_process_report.xml',
        'wizard/reject_request_wizard_view.xml',
        # 'wizard/reject_reason_mail_template.xml',
    ],
    'installable': True,
    'application': False,
}

# vim:expandtab:smar    tindent:tabstop=4:softtabstop=4:shiftwidth=4:
