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
	_name = 'import.employee.contract'
	_description = 'Import Employee Contract'

	file_type = fields.Selection([('XLS', 'XLS File')],string='File Type', default='XLS')
	file = fields.Binary(string="Upload File")

	def import_employee_contract(self):
		if not self.file:
			raise ValidationError(_("Please Upload File to Import Employee Contract!"))

		if self.file_type == 'XLS':
			try:
				file = tempfile.NamedTemporaryFile(delete= False,suffix=".xlsx")
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
					fields = list(map(lambda row:row.value.encode('utf-8'), sheet.row(row_no)))
				else:
					line = list(map(lambda row:isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value), sheet.row(row_no)))
					values.update( {
							'employee_code': line[0],
							'struct_id': line[1],
							'wage': line[2],
							'HRA': line[3],
							'TA': line[4],
							'cda': line[5],
							'mobile_allowance': line[6],
							'shift_allow': line[7],
							'remote_allow': line[8],
							'other_allow': line[9],
							'journal_id': line[10],
							'analytic_account_id': line[11],

					})
					res = self.create_contract(values)


	def create_contract(self, values):
		code = values.get('employee_code').upper()
		employee = self.env['hr.employee'].search([('employee_code','=',code)],limit=1)
		contract = self.env['hr.contract']
		struct_id = self.env['hr.payroll.structure'].search([('name', '=', values.get('struct_id'))],limit=1)
		journal_id = self.env['account.journal'].search([('name', '=', values.get('journal_id'))],limit=1)
		analytic_account_id = self.env['account.analytic.account'].search([('name', '=', values.get('analytic_account_id'))], limit=1)
		if not employee:
			print('Employee code %s is not available',values.get('employee_code'))
			#raise Warning(_('Employee Name is Required !'))
		if not struct_id:
			raise Warning(_('Salary Structure Name is Required !'))
		if not journal_id:
			raise Warning(_('Salary Journal is Required !'))
		department_id = employee.department_id.id
		print(values.get('shift_allow'))
		vals = {
			'name': 'Contract for ' + '(' + values.get('employee_code') + ')',
			'struct_id': struct_id.id,
			'employee_id': employee.id,
			'department_id': department_id,
			'wage': float(values.get('wage')),
			'HRA': float(values.get('HRA')),
			'is_HRA': True if float(values.get('HRA')) > 0 else False,
			'TA': float(values.get('TA')),
			'is_TA': True if float(values.get('TA')) > 0 else False,
			'cda': float(values.get('cda')),
			'is_cda': True if float(values.get('cda')) > 0 else False,
			'mobile_allowance': float(values.get('mobile_allowance')),
			'mobile': True if float(values.get('mobile_allowance')) > 0 else False,
			'shift_allow': float(values.get('shift_allow')),
			'is_shift_allow': True if float(values.get('shift_allow')) > 0 else False,
			'remote_allow': float(values.get('remote_allow')),
			'is_remote_allow': True if float(values.get('remote_allow')) > 0 else False,
			'other_allow': float(values.get('other_allow')),
			'is_other_allow': True if float(values.get('other_allow')) > 0 else False,
			'journal_id':journal_id.id,
			'analytic_account_id':analytic_account_id.id,
			'payslip_type':'normal',
			'state':'open'
		}

		if employee:
			res = contract.create(vals)
		return res



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: