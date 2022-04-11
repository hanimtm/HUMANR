from odoo import models, fields, api
import base64
import xlwt
from datetime import datetime, date
import datetime as dt
# from StringIO import StringIO
from io import BytesIO
import string
import math
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import calendar
from itertools import groupby
from operator import itemgetter

import logging
_logger = logging.getLogger(__name__)
# import pandas as pd


class WizardPayrollHistory(models.TransientModel):
    _name = 'wizard.payroll.history'
    _inherit = 'wizard.payroll.history'

    def export_payroll_xls(self):

        rowx = 7

        fl = BytesIO()
        style0 = xlwt.easyxf(
            'font: name Times New Roman, color-index red, bold 1;align : horiz center,vertical center;',
            num_format_str='#,##0.00')
        style1 = xlwt.easyxf(num_format_str='YYYY-MM-DD')
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Employee Payroll Report', cell_overwrite_ok=True)
        asset_catg_ids = True

        font = xlwt.Font()

        font.bold = True

        for_center = xlwt.easyxf(
            "font: name  Verdana, color black,  height 200; align: horiz center,vertical center,wrap yes; borders: top thin, bottom thin, left thin, right thin; pattern: pattern solid, fore_color %s;" % 'yellow')
        for_last_row = xlwt.easyxf(
            "font: name  Verdana, color black,  height 200; align: horiz center,vertical center; borders: top thin, bottom medium, left thin, right thin; pattern: pattern solid, fore_color %s;" % 'yellow')
        for_normal_border = xlwt.easyxf(
            "font:bold 1, name Verdana, color black, height 200; align: horiz center, vertical center, wrap yes; borders: top medium, bottom medium, left medium, right medium; pattern: pattern solid, fore_color %s;" % '100')
        for_no_border = xlwt.easyxf(
            "font: name Verdana, color black, height 200; align: horiz center, vertical center; borders: top thin, bottom thin, left thin, right thin; pattern: pattern solid, fore_color %s;" % '100')
        for_center_line = xlwt.easyxf(
            "font: name  Verdana, color black,  height 200; align: horiz center,vertical center; borders: top DASHED, bottom DASHED, left DASHED, right DASHED; pattern: pattern solid, fore_color %s;" % '100')

        for_center_total = xlwt.easyxf(
            "font: name  Verdana , color blue,  height 200, bold 1; align: horiz center,vertical center,wrap yes; borders: top_color red, bottom_color red, right_color red, left_color red,top medium, bottom medium, left medium, right medium; pattern: pattern solid, fore_color %s; " % '100')

        alignment = xlwt.Alignment()  # Create Alignment
        alignment.horz = xlwt.Alignment.HORZ_RIGHT
        style = xlwt.easyxf('align: wrap yes; borders: top thin, bottom thin, left thin, right thin;')
        style.num_format_str = '#,##0.00'

        style_net_sal = xlwt.easyxf(
            'font:bold 1; align: wrap yes; borders: top medium, bottom medium, left medium, right medium;')
        style_net_sal.num_format_str = '#,##0.00'

        for limit in range(1, 65536):
            worksheet.row(limit).height = 400

        worksheet.row(0).height = 1000
        worksheet.col(0).width = 4000
        worksheet.col(1).width = 6000
        worksheet.col(2).width = 6000
        worksheet.col(3).width = 10000
        worksheet.col(4).width = 7000
        worksheet.col(5).width = 4000

        borders = xlwt.Borders()
        borders.bottom = xlwt.Borders.MEDIUM
        border_style = xlwt.XFStyle()  # Create Style
        border_style.borders = borders
        inv_name_row = 6
        company = self.env.user.company_id.name

        # worksheet.write(0, 0, company, style0)
        worksheet.write_merge(0, 0, 0, 14, company, style0)
        worksheet.write_merge(1, 1, 0, 14, 'Payroll Report', style0)
        worksheet.write_merge(2, 2, 0, 14, '', style0)
        worksheet.write_merge(3, 3, 0, 14,
                              'For the Period (' + datetime.strptime(self.xlsx_date_from, '%Y-%m-%d').strftime(
                                  '%m/%d/%y') + '--' + datetime.strptime(self.xlsx_date_to,
                                                                         '%Y-%m-%d').strftime('%m/%d/%y') + ')',
                              style0)
        worksheet.write(inv_name_row, 0, 'Code', for_center)
        worksheet.write(inv_name_row, 1, 'Employee Name', for_center)
        worksheet.write(inv_name_row, 2, 'Department', for_center)
        worksheet.write(inv_name_row, 3, 'No of Days', for_center)
        sumcol = col = 4
        list_month = []
        for type in self.env['hr.salary.type'].search([], order="sequence asc"):
            worksheet.col(col).width = 4000
            worksheet.write(inv_name_row, col, type.name, for_center)
            list_month.append({'col': col, 'type': type.id})
            col += 1
        worksheet.write(inv_name_row, col, 'Payment Type', for_center)
        col += 1
        worksheet.write(inv_name_row, col, 'Net Salary', for_center)

        inv_name_row3 = 7
        ct = line_total = 0

        analysis = []
        for vals in self.env['hr.payslip'].sudo().search(
                [('date_from', '<=', self.xlsx_date_from), ('date_to', '>=', self.xlsx_date_to)]):
            work_data = vals.employee_id.get_work_days_data(datetime.strptime(str(self.xlsx_date_from), '%Y-%m-%d'),
                                                            datetime.strptime(str(self.xlsx_date_to), '%Y-%m-%d'),
                                                            calendar=vals.contract_id.resource_calendar_id)
            payment = 'Bank'
            if vals.journal_id.type == 'cash':
                payment = 'Cash'
            worksheet.write(inv_name_row3, 0, vals.employee_id.employee_code, for_center_line)
            worksheet.write(inv_name_row3, 1, vals.employee_id.full_name, for_center_line)
            worksheet.write(inv_name_row3, 2, vals.employee_id.department_id.name, for_center_line)
            worksheet.write(inv_name_row3, 3, vals.payment_days, for_center_line)
            for months in list_month:
                data = vals.line_ids.filtered(
                    lambda l: l.salary_type.id == months['type'] and l.code != 'GOSI_COMP' and abs(l.amount) > 0)
                amount = 0
                if data:
                    amount = sum(data.mapped('amount'))
                analysis += self.get_payslip_distribution(vals, months['type'], amount, months['col'], work_data)
                worksheet.write(inv_name_row3, months['col'], amount, for_center_line)
            worksheet.write(inv_name_row3, col - 1, payment, for_center_total)
            label = self.column_num_to_string(col)
            col_label = 'G' + str(inv_name_row3 + 1) + ':' + label + str(inv_name_row3 + 1)
            worksheet.write(inv_name_row3, col, xlwt.Formula('SUM(%s)' % col_label), for_center_total)

            # worksheet.write(inv_name_row3, col, dep.get('final_dispose_move'), for_center_line)
            # worksheet.write(inv_name_row3, col + 1, dep.get('balance'), for_center_line)
            inv_name_row3 += 1

        self.total_row_summary(worksheet, inv_name_row3 + 1, list_month)
        label = self.column_num_to_string(col + 1)
        col_label = label + '8:' + label + str(inv_name_row3)
        worksheet.write(inv_name_row3 + 1, col, xlwt.Formula('SUM(%s)' % col_label),
                        for_center_total)
        # analysis_sorted = sorted(analysis, key = lambda i: (i['project'],i['employee']),reverse=True)
        analysis_sorted = students = sorted(analysis,
                                            key=itemgetter('project', 'employee'))
        set_project = set([sub['project'] for sub in analysis_sorted])
        worksheet2 = workbook.add_sheet('Project-Wise Analysis', cell_overwrite_ok=True)
        asset_catg_ids = True

        for limit in range(1, 65536):
            worksheet.row(limit).height = 400

        worksheet2.row(0).height = 1000
        worksheet2.col(0).width = 4000
        worksheet2.col(1).width = 6000
        worksheet2.col(2).width = 6000
        worksheet2.col(3).width = 10000
        worksheet2.col(4).width = 7000
        worksheet2.col(5).width = 4000

        borders = xlwt.Borders()
        borders.bottom = xlwt.Borders.MEDIUM
        border_style = xlwt.XFStyle()  # Create Style
        border_style.borders = borders
        inv_name_row = 6
        company = self.env.user.company_id.name

        # worksheet.write(0, 0, company, style0)
        worksheet2.write_merge(0, 0, 0, 14, company, style0)
        worksheet2.write_merge(1, 1, 0, 14, 'Project-Wise Analysis', style0)
        worksheet2.write_merge(2, 2, 0, 14, '', style0)
        worksheet2.write_merge(3, 3, 0, 14,
                               'For the Period (' + datetime.strptime(self.xlsx_date_from, '%Y-%m-%d').strftime(
                                   '%m/%d/%y') + '--' + datetime.strptime(self.xlsx_date_to,
                                                                          '%Y-%m-%d').strftime('%m/%d/%y') + ')',
                               style0)
        worksheet2.write(inv_name_row, 0, 'Project', for_center)
        worksheet2.write(inv_name_row, 1, 'Code', for_center)
        worksheet2.write(inv_name_row, 2, 'Employee Name', for_center)
        sumcol = col = 3
        list_month = []
        for type in self.env['hr.salary.type'].search([], order="sequence asc"):
            worksheet2.col(col).width = 4000
            worksheet2.write(inv_name_row, col, type.name, for_center)
            list_month.append({'col': col, 'type': type.id})
            col += 1

        worksheet2.write(inv_name_row, col, 'Total', for_center)
        inv_name_row3 = 7
        ct = line_total = 0
        analysis = []
        for vals in set_project:
            analytic = self.env['account.analytic.account'].sudo().search([('id', '=', vals)])
            data_list = [item for item in analysis_sorted if item['project'] == vals]
            for key, value in groupby(data_list,
                                      key=itemgetter('employee')):
                employee_id = self.env['hr.employee'].sudo().search([('id', '=', key)])
                for data in value:
                    worksheet2.write(inv_name_row3, 0, analytic.name, for_center_line)
                    worksheet2.write(inv_name_row3, 1, employee_id.employee_code, for_center_line)
                    worksheet2.write(inv_name_row3, 2, employee_id.full_name, for_center_line)
                    for months in list_month:
                        if months['type'] == data['type']:
                            worksheet2.write(inv_name_row3, months['col'], data['amount'], for_center_line)

                label = self.column_num_to_string(col)
                col_label = 'F' + str(inv_name_row3 + 1) + ':' + label + str(inv_name_row3 + 1)
                worksheet2.write(inv_name_row3, col, xlwt.Formula('SUM(%s)' % col_label), for_center_total)
                inv_name_row3 += 1

        self.total_row_summary(worksheet2, inv_name_row3, list_month)
        label = self.column_num_to_string(col + 1)
        col_label = label + '8:' + label + str(inv_name_row3)
        worksheet2.write(inv_name_row3, col, xlwt.Formula('SUM(%s)' % col_label),
                         for_center_total)
        # for k, v in groupby(data_list, key=lambda x: x['employee']):
        #     analytic = self.env['account.analytic.account'].sudo().search([('id', '=', vals)])
        #     inv_name_row3 += 1
        #     print(list_month)
        #     for data in list(v):
        #         if k == data['employee']:
        #             print(data)
        #             employee_id = self.env['hr.employee'].sudo().search([('id', '=', data['employee'])])
        #             worksheet2.write(inv_name_row3, 0, analytic.name, for_center_line)
        #             worksheet2.write(inv_name_row3, 1, employee_id.employee_code, for_center_line)
        #             worksheet2.write(inv_name_row3, 2, employee_id.full_name, for_center_line)
        #             for months in list_month:
        #                 worksheet2.write(inv_name_row3, months['col'], data['amount'], for_center_line)
        workbook.save(fl)
        fl.seek(0)

        name_file = 'Payroll Report.xls'

        self.write({
            'report_file': base64.encodestring(fl.getvalue()),
            'name': name_file})

        self.visible = False
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'wizard.payroll.history',
            'target': 'new',
            'res_id': self.id,
        }