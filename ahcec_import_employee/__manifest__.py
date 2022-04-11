# -*- coding: utf-8 -*-
{
    'name': "Import Employee from Excel",
    'version': "11.0.0.0",
    'category': "Employees",
    'summary': "Import Employee from Excel",
    'description':
        """
            Import Employee from Excel
        """,
    'author': "Aneesh.AV",
    'depends': ['base', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/import_employee_view.xml',
        'views/import_employee_menu.xml',
    ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
