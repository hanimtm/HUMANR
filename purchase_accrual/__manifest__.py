# -*- coding: utf-8 -*-
###################################################################################
#    Purchase Accrual <https://ahcec.com>
#
#    GAIT Co Pvt. Ltd.
#    Copyright (C) 2019-TODAY AHCEC (<https://ahcec.com>).
#    Author: Aneesh AV (<https://ahcec.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################
{
    'name': 'Purchase Accrual',
    'version': '11.0.1.0.0',
    'summary': 'Purchase Accrual',
    'description': """
        This module will create Accrual Accounting Entries from Purchase
        """,
    'category': 'Purchase',
    'author': "Aneesh.AV",
    'company': 'AHCEC',
    'maintainer': 'AHCEC',
    'website': "https://ahcec.com",
    'depends': [
        'purchase', 'account', 'stock'
    ],
    'data': [
        #    'security/ir.model.access.csv',
        #    'security/security.xml',
        #    'views/hr_loan_seq.xml',
        #    'data/salary_rule_loan.xml',
        #    'views/hr_loan.xml',
        'views/purchase.xml',
        'views/product.xml',
        'views/data.xml',
    ],
    'demo': [],
    'images': [],  # 'static/description/banner.jpg'],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
