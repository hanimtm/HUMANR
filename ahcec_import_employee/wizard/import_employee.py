# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import io
import xlrd
import babel
import logging
import tempfile
import binascii
from io import StringIO
from datetime import date, datetime, time
from odoo import api, fields, models, tools, _
from odoo.exceptions import Warning, UserError, ValidationError

_logger = logging.getLogger(__name__)

try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')
try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')
try:
    import cStringIO
except ImportError:
    _logger.debug('Cannot `import cStringIO`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


class ImportEmployee(models.TransientModel):
    _name = 'import.employee'
    _description = 'Import Employee'

    file_type = fields.Selection([('XLS', 'XLS File')], string='File Type', default='XLS')
    file = fields.Binary(string="Upload File")

    def import_employee(self):
        if not self.file:
            raise ValidationError(_("Please Upload File to Import Employee !"))

        if self.file_type == 'XLS':
            line = keys = [
                'employee_code',  # 0
                'name',  # 1
                'middle_name',  # 2
                'last_name',  # 3
                'arabic_name',  # 4
                'job_title',  # 5
                'department_id',  # 6
                'mobile_phone',  # 7
                'address_home_id',  # 8
                'religion',  # 9
                'work_phone',  # 10
                'work_email',  # 11
                'department_id',  # 12
                'address_id',  # 13
                'gender',  # 14
                'birthday',  # 15
                'marital',  # 16
                'joining_date',  # 17
                'work_email',  # 18
                'work_mobile'  # 19
            ]

            try:
                file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                file.write(binascii.a2b_base64(self.file))
                file.seek(0)
                values = {}
                workbook = xlrd.open_workbook(file.name)
                sheet = workbook.sheet_by_index(0)
            except Exception:
                raise ValidationError(_("Please Select Valid File Format !"))

            for row_no in range(sheet.nrows):
                val = {}
                if row_no <= 0:
                    fields = list(map(lambda row: row.value.encode('utf-8'), sheet.row(row_no)))
                else:
                    line = list(
                        map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value),
                            sheet.row(row_no)))
                    values.update({
                        'employee_code': line[0],
                        'name': line[1],
                        'middle_name': line[2],
                        'last_name': line[3],
                        'arabic_name': line[4],
                        'job_title': line[5],
                        'department_id': line[6],
                        'mobile_phone': line[7],
                        'address_home_id': line[8],
                        'religion': line[9],
                        'work_phone': line[10],
                        'work_email': line[11],
                        'gender': line[12],
                        'birthday': line[13],
                        'marital': line[14],
                        'joining_date': line[15],
                        'work_mobile': line[16],
                        'identification_id': line[17],
                    })
                    res = self.create_employee(values)

    def create_employee(self, values):
        employee = self.env['hr.employee']
        department_id = self.get_department(values.get('department_id'))
        address_id = self.get_address(values.get('employee_code'), values.get('name'))
        birthday = self.get_birthday(values.get('birthday'))
        marital = 'married' if values.get('marital') == 'Married' else 'single'
        religion = 'muslim' if values.get('religion') == 'Muslim' else 'non-muslim'
        if department_id:
            manager = department_id.manager_id.id

        if values.get('gender') == 'Male':
            gender = 'male'
        elif values.get('gender') == 'male':
            gender = 'male'
        elif values.get('gender') == 'Female':
            gender = 'female'
        elif values.get('gender') == 'female':
            gender = 'female'
        elif values.get('gender') == 'Other':
            gender = 'other'
        elif values.get('gender') == 'other':
            gender = 'other'
        else:
            gender = 'male'

        vals = {
            'employee_code': values.get('employee_code'),
            'name': values.get('name'),
            'middle_name': values.get('middle_name'),
            'last_name': values.get('last_name'),
            'arabic_name': values.get('arabic_name'),
            'job_title': values.get('job_title'),
            'department_id': department_id.id,
            'mobile_phone': values.get('mobile_phone'),
            'address_home_id': address_id.id,
            'religion': religion,
            'work_phone': values.get('work_phone'),
            'work_email': values.get('work_email'),
            'gender': gender,
            'birthday': birthday,
            'marital': marital,
            'joining_date': values.get('joining_date'),
            'work_mobile': values.get('work_mobile'),
            'identification_id': values.get('identification_id'),
            'parent_id': manager,
        }

        if values.get('name') == '':
            raise Warning(_('Employee Name is Required !'))
        if values.get('department_id') == '':
            raise Warning(_('Department Field can not be Empty !'))

        available = self.env['hr.employee'].search([('employee_code', '=', values.get('employee_code'))])
        if not available:
            res = employee.create(vals)
        else:
            res = available  # employee.write(vals)
        return res

    def get_department(self, name):
        department = self.env['hr.department'].search([('name', '=', name)], limit=1)
        if department:
            return department
        else:
            raise UserError(_('"%s" Department is not found in system !') % name)

    def get_address(self, employee_code, name):
        address = self.env['res.partner'].search([('partner_no', '=', employee_code)], limit=1)
        if address:
            return address
        else:
            address = self.env['res.partner'].create({
                'name': employee_code, 'partner_no': name,})
            return address

    def get_birthday(self, date):
        try:
            if date:
                birthday = datetime.strptime(date, '%Y/%m/%d')
                return birthday
            else:
                return ''
        except Exception:
            raise ValidationError(_('Wrong Date Format ! Date Should be in format YYYY/MM/DD'))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
