# -*- coding: utf-8 -*-

from odoo import models, api, _, fields
from datetime import date as dt, datetime
import calendar


class AccrualWizard(models.TransientModel):
    _name = 'accrual.wizard'

    date_from = fields.Date('From', required=True)
    date_to = fields.Date('To', required=True)

    @api.onchange('date_from')
    def onchange_date_from(self):
        if self.date_from:
            month = datetime.strptime(str(self.date_from), '%Y-%m-%d').month
            year = datetime.strptime(str(self.date_from), '%Y-%m-%d').year
            sdate = dt(year, month, 1)
            edate = dt(year, month, calendar.monthrange(year, month)[1])
            self.date_from = sdate
            self.date_to = edate

    @api.onchange('date_to')
    def onchange_date_to(self):
        if self.date_from:
            month = datetime.strptime(str(self.date_to), '%Y-%m-%d').month
            year = datetime.strptime(str(self.date_to), '%Y-%m-%d').year
            sdate = dt(year, month, 1)
            edate = dt(year, month, calendar.monthrange(year, month)[1])
            self.date_from = sdate
            self.date_to = edate

    def get_timesheet(self, employee, date_from, date_to):
        self.env.cr.execute("""SELECT sum(unit_amount) as hours,account_id FROM account_analytic_line
                                                                   WHERE employee_id = %s and
                                                                   date >= %s and
                                                                   date <= %s and 
                                                                   sheet_id is not Null
                                                                   group by account_id
                                                                        """, (
            employee, date_from, date_to,))
        data = self.env.cr.dictfetchall()
        return data

    def hr_accrual_entry(self):
        for employee in self.env['hr.employee'].search([('active', '=', True)]):
            contracts = employee.get_active_contracts(date=self.date_to)
            month = datetime.strptime(str(self.date_from), '%Y-%m-%d').month
            year = datetime.strptime(str(self.date_from), '%Y-%m-%d').year
            sdate = dt(year, month, 1)
            # edate = dt(year, month, calendar.monthrange(year, month)[1])

            for cont in contracts:
                timesheets = self.get_timesheet(employee.id, self.date_from, self.date_to)

                work_data = cont.employee_id.get_work_days_data(datetime.strptime(str(self.date_from), '%Y-%m-%d'),
                                                                datetime.strptime(str(self.date_to), '%Y-%m-%d'),
                                                                calendar=cont.resource_calendar_id)

                if cont.state in ('open', 'pending'):
                    # end of service accrual entry
                    if cont.is_eos_amount:
                        line_ids = []
                        amount = cont.eos_amount
                        if cont.eos_accrual_move_id:
                            amount = amount - cont.eos_accrual_move_id.amount
                        move = {
                            'name': '/',
                            'journal_id': cont.company_id.accrual_journal.id,
                            'date': self.date_to,
                        }
                        debit_account = int(self.env['ir.config_parameter'].sudo().get_param('eos_debit_account'))
                        credit_account = int(self.env['ir.config_parameter'].sudo().get_param('eos_credit_account'))

                        if debit_account and credit_account:
                            adjust_credit = (0, 0, {
                                'name': cont.employee_id.name or '/ ' + 'EOS',
                                'partner_id': cont.employee_id.address_home_id.id,
                                'account_id': credit_account,
                                'journal_id': cont.company_id.accrual_journal.id,
                                'date': self.date_to,
                                'credit': amount,
                                'debit': 0.0,
                            })
                            print('adjust_credit Amount ::: %s ', amount)
                            line_ids.append(adjust_credit)
                            total_sheet = 0
                            if timesheets:
                                for sheet in timesheets:
                                    if sheet.get('account_id'):
                                        isdepartment = self.env['account.analytic.account'].browse(
                                            sheet.get('account_id')).isdepartment
                                        if isdepartment:
                                            debit_account = int(
                                                self.env['ir.config_parameter'].sudo().get_param(
                                                    'eos_debit_pjt_account'))
                                    amt = abs((amount / work_data['hours']) * sheet.get('hours'))
                                    total_sheet = total_sheet + amt
                                    print('Amount ::: %s ', total_sheet)
                                    adjust_debit = (0, 0, {
                                        'name': cont.employee_id.name or '/ ' + 'EOS Accrual',
                                        'partner_id': cont.employee_id.address_home_id.id,
                                        'account_id': debit_account,
                                        'journal_id': cont.company_id.accrual_journal.id,
                                        'analytic_account_id': sheet.get('account_id') or False,
                                        'date': self.date_to,
                                        'debit': amt,
                                        'credit': 0.0,
                                    })
                                    line_ids.append(adjust_debit)
                            print('First Amount ::: %s ', total_sheet)
                            amount = amount - total_sheet
                            if amount != 0:
                                print('Amount ::: %s ', amount)
                                adjust_debit = (0, 0, {
                                    'name': cont.employee_id.name or '/ ' + 'EOS Accrual',
                                    'partner_id': cont.employee_id.address_home_id.id,
                                    'account_id': debit_account,
                                    'journal_id': cont.company_id.accrual_journal.id,
                                    'analytic_account_id': cont.analytic_account_id.id or False,
                                    'date': self.date_to,
                                    'debit': abs(amount),
                                    'credit': 0.0,
                                })
                                line_ids.append(adjust_debit)

                            move['line_ids'] = line_ids
                            move_id = self.env['account.move'].create(move)
                            cont.write({'eos_accrual_move_id': move_id.id})
                            accrual = {
                                'move_id': move_id.id,
                                'employee_id': cont.employee_id.id,
                                'date_from': self.date_from,
                                'date_to': self.date_to,
                                'type': 'eos',
                            }
                            self.env['employee.accrual.move'].sudo().create(accrual)
                    if cont.is_vacation:
                        line_ids = []
                        date = datetime.strptime(self.date_to, '%Y-%m-%d')
                        month_days = calendar.monthrange(date.year, date.month)[1]
                        amount = ((cont.vacation / 12) / 30) * month_days

                        move = {
                            'name': '/',
                            'journal_id': cont.company_id.accrual_journal.id,
                            'date': self.date_to,
                        }

                        debit_account = int(self.env['ir.config_parameter'].sudo().get_param('vacation_debit_account'))
                        credit_account = int(
                            self.env['ir.config_parameter'].sudo().get_param('vacation_credit_account'))

                        if debit_account and credit_account:
                            adjust_credit = (0, 0, {
                                'name': 'Vacation Accrual',
                                'partner_id': cont.employee_id.address_home_id.id,
                                'account_id': credit_account,
                                'journal_id': cont.company_id.accrual_journal.id,
                                'date': self.date_to,
                                'credit': amount,
                                'debit': 0.0,
                            })
                            line_ids.append(adjust_credit)
                            total_sheet = 0
                            if timesheets:
                                for sheet in timesheets:
                                    if sheet.get('account_id'):
                                        isdepartment = self.env['account.analytic.account'].browse(
                                            sheet.get('account_id')).isdepartment
                                        if isdepartment:
                                            debit_account = int(
                                                self.env['ir.config_parameter'].sudo().get_param(
                                                    'vacation_debit_pjt_account'))
                                    amt = (amount / work_data['hours']) * sheet.get('hours')
                                    total_sheet = total_sheet + amt
                                    print('Amount ::: %s ', total_sheet)
                                    adjust_debit = (0, 0, {
                                        'name': 'Vacation Accrual',
                                        'partner_id': cont.employee_id.address_home_id.id,
                                        'account_id': debit_account,
                                        'journal_id': cont.company_id.accrual_journal.id,
                                        'analytic_account_id': sheet.get('account_id') or False,
                                        'date': self.date_to,
                                        'debit': amt,
                                        'credit': 0.0,
                                    })
                                    line_ids.append(adjust_debit)
                            print('First Amount ::: %s ', total_sheet)
                            amount = amount - total_sheet
                            if amount != 0:
                                print('Amount ::: %s ', amount)
                                adjust_debit = (0, 0, {
                                    'name': 'Vacation Accrual',
                                    'partner_id': cont.employee_id.address_home_id.id,
                                    'account_id': debit_account,
                                    'journal_id': cont.company_id.accrual_journal.id,
                                    'analytic_account_id': cont.analytic_account_id.id or False,
                                    'date': self.date_to,
                                    'debit': abs(amount),
                                    'credit': 0.0,
                                })
                                line_ids.append(adjust_debit)

                            move['line_ids'] = line_ids
                            move_id = self.env['account.move'].create(move)
                            accrual = {
                                'move_id': move_id.id,
                                'employee_id': cont.employee_id.id,
                                'date_from': self.date_from,
                                'date_to': self.date_to,
                                'type': 'vacation',
                            }
                            self.env['employee.accrual.move'].sudo().create(accrual)

                    if cont.air_allowance:
                        line_ids = []
                        date = datetime.strptime(self.date_to, '%Y-%m-%d')
                        month_days = calendar.monthrange(date.year, date.month)[1]
                        amount = ((cont.ticket_total / 12) / 30) * month_days

                        move = {
                            'name': '/',
                            'journal_id': cont.company_id.accrual_journal.id,
                            'date': self.date_to,
                        }

                        debit_account = int(self.env['ir.config_parameter'].sudo().get_param('ticket_debit_account'))
                        credit_account = int(
                            self.env['ir.config_parameter'].sudo().get_param('ticket_credit_account'))

                        if debit_account and credit_account:
                            adjust_credit = (0, 0, {
                                'name': 'Ticket Accrual',
                                'partner_id': cont.employee_id.address_home_id.id,
                                'account_id': credit_account,
                                'journal_id': cont.company_id.accrual_journal.id,
                                'date': self.date_to,
                                'credit': amount,
                                'debit': 0.0,
                            })
                            line_ids.append(adjust_credit)
                            total_sheet = 0
                            if timesheets:
                                for sheet in timesheets:
                                    if sheet.get('account_id'):
                                        isdepartment = self.env['account.analytic.account'].browse(
                                            sheet.get('account_id')).isdepartment
                                        if isdepartment:
                                            debit_account = int(
                                                self.env['ir.config_parameter'].sudo().get_param(
                                                    'ticket_debit_pjt_account'))
                                    amt = (amount / work_data['hours']) * sheet.get('hours')
                                    total_sheet = total_sheet + amt
                                    print('Amount ::: %s ', total_sheet)
                                    adjust_debit = (0, 0, {
                                        'name': 'Ticket Accrual',
                                        'partner_id': cont.employee_id.address_home_id.id,
                                        'account_id': debit_account,
                                        'journal_id': cont.company_id.accrual_journal.id,
                                        'analytic_account_id': sheet.get('account_id') or False,
                                        'date': self.date_to,
                                        'debit': amt,
                                        'credit': 0.0,
                                    })
                                    line_ids.append(adjust_debit)
                            print('First Amount ::: %s ', total_sheet)
                            amount = amount - total_sheet
                            if amount != 0:
                                print('Amount ::: %s ', amount)
                                adjust_debit = (0, 0, {
                                    'name': 'Ticket Accrual',
                                    'partner_id': cont.employee_id.address_home_id.id,
                                    'account_id': debit_account,
                                    'journal_id': cont.company_id.accrual_journal.id,
                                    'analytic_account_id': cont.analytic_account_id.id or False,
                                    'date': self.date_to,
                                    'debit': abs(amount),
                                    'credit': 0.0,
                                })
                                line_ids.append(adjust_debit)

                            move['line_ids'] = line_ids
                            move_id = self.env['account.move'].create(move)
                            accrual = {
                                'move_id': move_id.id,
                                'employee_id': cont.employee_id.id,
                                'date_from': self.date_from,
                                'date_to': self.date_to,
                                'type': 'ticket',
                            }
                            self.env['employee.accrual.move'].sudo().create(accrual)
