{
    'name': "Middle East Human Resource",
    'summary': """ Human Resource Management """,
    'description': """
        Human Resource Management specific for middle east companies
    """,
    'author': 'ahcec',
    'website': 'http://www.ahcec.com',
    'category': 'HR',
    'version': '1.0',
    'sequence': 20,
    'depends': ['base', 'hr', 'hr_recruitment',  'ahcec_hr_groups_configuration', 'mail', 'hr_fiscal_year', 'contacts'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/mail_channel_demo.xml',
        'views/hr_view.xml',
        'wizard/employee_head_count_report_view.xml',
        'wizard/employee_head_count_report_template.xml',
        'wizard/new_joining_report_view.xml',
        'wizard/new_joining_report_template.xml',
        'views/res_partner_view.xml',
        'views/hr_job_view.xml',
        'views/email_template_view.xml',
        'views/cron.xml',
        'views/res_company_view.xml',
        'menu.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
