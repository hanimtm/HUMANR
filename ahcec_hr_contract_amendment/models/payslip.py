from datetime import datetime, timedelta
from datetime import time as datetime_time
from odoo import api, models, fields, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError
from itertools import groupby
import pytz, logging
_logger = logging.getLogger(__name__)
from datetime import datetime


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    salary_type = fields.Many2one('hr.salary.type', string='Type')

class Employee(models.Model):
    _inherit = 'hr.employee'

    is_aramco_smdcad = fields.Boolean('Employee is Aramco SMPCAD')


class Contract(models.Model):
    _inherit = 'hr.contract'

    is_aramco_smdcad = fields.Boolean('Employee is Aramco SMPCAD')

    def get_basics(self, payslip, type, value):
        for data in self:
            contracts = self.env['hr.contract'].browse(data.id)
            amount = 0
            previous_basics = data.env['contract.package.line'].sudo().search(
                [('name', '=', 'basic'), ('employee_id', '=', data.employee_id.id), ('state', '=', 'done'),
                 ('effective_date', '<=', payslip.date_from)], order="effective_date desc", limit=1)

            current_basics = data.env['contract.package.line'].sudo().search(
                [('name', '=', type), ('employee_id', '=', data.employee_id.id), ('state', '=', 'done'),
                 ('effective_date', '>=', payslip.date_from), ('effective_date', '<=', payslip.date_to)],
                order="effective_date asc")
            previous_basic = value
            previous_date = payslip.date_from
            if previous_basics:
                previous_basic = previous_basics.new_package

            ct = 0
            fmt = '%Y-%m-%d'
            if contracts.amendment_count > 0:
                for changes in current_basics:
                    if ct == 0:
                        d1 = datetime.strptime(str(changes.effective_date), fmt)
                        d2 = datetime.strptime(str(previous_date), fmt)
                        no_of_days = abs((d1 - d2).days)
                        amount += self.get_amount_day(data, contracts, changes, previous_date, payslip, no_of_days,
                                                      previous_basic)
                        previous_basic = changes.new_package
                        previous_date = changes.effective_date
                        ct += 1
                    else:
                        d1 = datetime.strptime(str(changes.effective_date), fmt)
                        d2 = datetime.strptime(str(previous_date), fmt)
                        no_of_days = abs((d1 - d2).days)
                        amount += self.get_amount_day(data, contracts, changes, previous_date, payslip, no_of_days,
                                                      previous_basic)
                        previous_basic = changes.new_package
                        previous_date = changes.effective_date
                        ct += 1

                    if ct == len(current_basics):
                        d1 = datetime.strptime(str(changes.effective_date), fmt)
                        d2 = datetime.strptime(str(payslip.date_to), fmt)
                        no_of_days = abs((d1 - d2).days) + 1
                        amount += self.get_amount_day(data, contracts, changes, payslip.date_to, payslip, no_of_days,
                                                      previous_basic)


            else:
                amount = (value * payslip.payment_days) / payslip.month_days
            return amount

    def get_amount_day(self, data, contracts, changes, previous_date, payslip, no_of_days, amt):
        result = data.get_worked_day_lines(contracts, previous_date, changes.effective_date)
        amount = 0
        leave_days = sum([sub['number_of_days'] for sub in result if sub['code'] == 'unpaid_leave'])
        annual_leaves = sum([sub['number_of_days'] for sub in result if sub['code'] in ('sick_leaves', 'annual_leave')])
        month_days = payslip.month_days
        leave_days = leave_days
        annual_leaves = annual_leaves
        payment_days = no_of_days - leave_days
        amount += (amt * payment_days) / month_days
        return amount

    @api.model
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        @param contract: Browse record of contracts
        @return: returns a list of dict containing the input that should be applied for the given contract between date_from and date_to
        """

        res = []
        if type(contracts) is not list:

            for contract in contracts:
                day_from = datetime.combine(fields.Date.from_string(date_from), datetime_time.min)
                day_to = datetime.combine(fields.Date.from_string(date_to), datetime_time.max)
                # compute leave days
                leaves = {}
                holiday_list = []
                leave_detail_list = []
                nb_of_days = (day_to - day_from).days + 1
                for day in range(0, nb_of_days):

                    day_from_start = datetime.strptime(((day_from + timedelta(days=day)).strftime("%Y-%m-%d 00:00:00")),
                                                       DEFAULT_SERVER_DATETIME_FORMAT)
                    day_from_end = datetime.strptime(((day_from + timedelta(days=day)).strftime("%Y-%m-%d 23:59:59")),
                                                     DEFAULT_SERVER_DATETIME_FORMAT)
                    holiday_ids = self.env['hr.holidays'].sudo().search([('type', '=', 'remove'),
                                                                  ('employee_id', '=', contracts.employee_id.id),
                                                                  ('state', '=', 'validate'),
                                                                  '|',
                                                                  '&',
                                                                  ('date_from', '>=', str(day_from_start)),
                                                                  ('date_from', '<=', str(day_from_end)),
                                                                  '&',
                                                                  ('date_to', '>=', str(day_from_start)),
                                                                  ('date_to', '<=', str(day_from_end))
                                                                  ])
                    leave_details = self.env['leave.detail'].sudo().search([('holiday_id', 'in', holiday_ids.ids),
                                                                     ('period_id.date_start', '<=',
                                                                      str(day_from_start.date())),
                                                                     ('period_id.date_stop', '>=',
                                                                      str(day_from_start.date())),
                                                                     ])
                    leave_detail_list.extend(leave_details.ids)
                    if holiday_ids:
                        holiday_list.extend(holiday_ids.ids)

                leave_detail_list = self.env['leave.detail'].sudo().browse(list(set(leave_detail_list)))
                leave_detail_object = self.env['leave.detail']
                for leave_detail in sorted(leave_detail_list, key=lambda l: l.holiday_id.holiday_status_id.id):
                    leave_detail_object += leave_detail
                paid_leave_days_list = []
                paid_leave_hours_list = []
                total_leave_day_list = []
                total_leave_hours_list = []

                for holiday_status_id, lines in groupby(leave_detail_object,
                                                        lambda l: l.holiday_id.holiday_status_id.id):
                    values = list(lines)

                    holiday_status_id = self.env['hr.holidays.status'].sudo().browse(holiday_status_id)
                    paid_leave_days_list.append(sum([detail.paid_leave for detail in values]))
                    paid_leave_hours_list.append(sum([detail.leave_hours for detail in values]))
                    total_leave_day_list.append(sum([detail.total_leave for detail in values]))
                    total_leave_hours_list.append(sum([detail.total_leave_hours for detail in values]))
                    leave_detail_obj = self.env['leave.detail']
                    for detail in values:
                        leave_detail_obj += detail
                    if leave_detail_obj.filtered(lambda l: l.unpaid_leave):
                        current_leave_struct = leaves.setdefault(holiday_status_id, {
                            'name': holiday_status_id.name + ' Working Days unpaid at 100%',
                            'sequence': 5,
                            'code': holiday_status_id.code or holiday_status_id.name,
                            'number_of_days': sum([detail.unpaid_leave for detail in values]),
                            'number_of_hours': sum([detail.unpaid_leave_hours for detail in values]),
                            'contract_id': contract.id,
                        })

                # compute unpaidleaves
                paid_leave_dict = {}
                if paid_leave_days_list:
                    paid_leave_dict = {
                        'name': _("Leave Working Days paid at 100%"),
                        'sequence': 2,
                        'code': 'annual_leave',
                        'number_of_days': sum(paid_leave_days_list),
                        'number_of_hours': sum(paid_leave_hours_list),
                        'contract_id': contract.id,
                    }
                # compute worked days
                work_data = contracts.employee_id.get_work_days_data(day_from, day_to,
                                                                     calendar=contracts.resource_calendar_id)
                leave_days = contracts.employee_id.get_leaves_day_count(day_from, day_to,
                                                                        calendar=contracts.resource_calendar_id)
                leave_hours = self.get_leaves_hours_count(day_from, day_to, employee_id=contracts.employee_id,
                                                          calendar=contracts.resource_calendar_id)

                attendances = {
                    'name': _("Normal Working Days paid at 100%"),
                    'sequence': 1,
                    'code': 'WORK100',
                    'number_of_days': float(float(work_data['days']) + leave_days) - sum(total_leave_day_list),
                    'number_of_hours': float(float(work_data['hours']) + leave_hours) - sum(total_leave_hours_list),
                    'contract_id': contract.id,
                }
                res.append(attendances)
                if paid_leave_dict:
                    res.append(paid_leave_dict)
                res.extend(leaves.values())
            return res

    def get_leaves_hours_count(self, from_datetime, to_datetime, employee_id, calendar=None):
        hours_count = 0.0
        calendar = calendar or self.resource_calendar_id
        for day_intervals in calendar._iter_leave_intervals(from_datetime, to_datetime, employee_id.resource_id.id):
            theoric_hours = employee_id.get_day_work_hours_count(day_intervals[0][0].date(), calendar=calendar)
            leave_time = sum((interval[1] - interval[0] for interval in day_intervals), timedelta())
            leave_time = float(float(leave_time.seconds / 60.0) / 60.0)
            hours_count += leave_time

        return hours_count


class Payslip(models.Model):
    _inherit = 'hr.payslip'

    gosi_for_employee = fields.Float('Gosi - Employee')

    def action_payslip_done_new(self):
        ctx = self._context.copy()
        # res = super(HrPayslip, self).action_payslip_done()
        # try:
        for slip in self:

            work_data = self.get_work_days_data(datetime.strptime(str(self.date_from), '%Y-%m-%d'),
                                                datetime.strptime(str(self.date_to), '%Y-%m-%d'),
                                                calendar=self.contract_id.resource_calendar_id)
            if round(work_data['hours']) < slip.total_timesheet_hours:
                work_data['hours'] = slip.total_timesheet_hours

            if not self.move_id:
                precision = self.env['decimal.precision'].precision_get('Payroll')
                line_ids = []
                debit_sum = 0.0
                credit_sum = 0.0
                date = slip.date or slip.date_to

                name = _('Payslip of %s') % (slip.employee_id.name)
                move_dict = {
                    'narration': name,
                    'ref': slip.number,
                    'journal_id': slip.journal_id.id,
                    'date': date,
                }
                total_debit = 0
                for line in slip.details_by_salary_rule_category:
                    if line.code not in ('GROSS', 'GOSI_COMP', 'NET', 'BASIC') and abs(line.amount) > 0:
                        if line.dummy_account:
                            debit_account_id = line.dummy_account.id
                            credit_account_id = line.dummy_account.id
                        else:
                            debit_account_id = line.salary_rule_id.account_debit.id
                            credit_account_id = line.salary_rule_id.account_credit.id

                        amount = slip.credit_note and -line.total or line.total
                        total_sheet = 0.0
                        if self.timesheet_ids:
                            for sheet in self.timesheet_ids:
                                if not sheet.name.isdepartment:
                                    if line.dummy_account:
                                        debit_account_id = line.dummy_account.id
                                        credit_account_id = line.dummy_account.id
                                    else:
                                        debit_account_id = line.salary_rule_id.project_account_debit.id
                                        credit_account_id = line.salary_rule_id.project_account_credit.id
                                amt = ((amount / (work_data['hours'])) * sheet.total_hours)
                                total_sheet = total_sheet + amt
                                if line.category_id.code in ('DED', 'GOSI'):
                                    adjust_debit = (0, 0, {
                                        'name': slip.employee_id.name or '/ ' + line.names,
                                        'partner_id': slip.employee_id.address_home_id.id,
                                        'account_id': debit_account_id,
                                        'journal_id': slip.company_id.accrual_journal.id,
                                        'analytic_account_id': sheet.name.id or False,
                                        'date': self.date_to,
                                        'credit': round(abs(amt), 2),
                                        'debit': 0.0,
                                    })
                                    total_debit -= round(abs(amt), 2)
                                    line_ids.append(adjust_debit)
                                else:
                                    adjust_debit = (0, 0, {
                                        'name': slip.employee_id.name or '/ ' + line.names,
                                        'partner_id': slip.employee_id.address_home_id.id,
                                        'account_id': debit_account_id,
                                        'journal_id': slip.company_id.accrual_journal.id,
                                        'analytic_account_id': sheet.name.id or False,
                                        'date': self.date_to,
                                        'debit': amt > 0.0 and round(amt, 2) or 0.0,
                                        'credit': amt < 0.0 and -round(amt, 2) or 0.0,
                                    })
                                    total_debit += round(amt, 2)
                                    line_ids.append(adjust_debit)
                            amount = amount - total_sheet
                            if amount != 0:
                                if line.category_id.code in ('DED', 'GOSI'):
                                    adjust_debit = (0, 0, {
                                        'name': self.employee_id.name or '/ ' + self.name,
                                        'partner_id': self.employee_id.address_home_id.id,
                                        'account_id': debit_account_id,
                                        'journal_id': self.company_id.accrual_journal.id,
                                        'analytic_account_id': self.contract_id.analytic_account_id.id or False,
                                        'date': self.date_to,
                                        'credit': round(abs(amount), 2),
                                        'debit': 0.0,
                                    })
                                    total_debit -= round(abs(amount), 2)
                                    line_ids.append(adjust_debit)
                                else:
                                    adjust_debit = (0, 0, {
                                        'name': self.employee_id.name or '/ ' + self.name,
                                        'partner_id': self.employee_id.address_home_id.id,
                                        'account_id': debit_account_id,
                                        'journal_id': self.company_id.accrual_journal.id,
                                        'analytic_account_id': self.contract_id.analytic_account_id.id or False,
                                        'date': self.date_to,
                                        # 'debit': round(abs(amount), 2),
                                        'debit': amount > 0.0 and round(amount, 2) or 0.0,
                                        'credit': amount < 0.0 and -round(amount, 2) or 0.0,
                                        # 'credit': 0.0,
                                    })
                                    total_debit += round(amount, 2)
                                    line_ids.append(adjust_debit)
                        else:
                            amount = slip.credit_note and -line.total or line.total
                            if line.dummy_account:
                                debit_account_id = line.dummy_account.id
                                credit_account_id = line.dummy_account.id
                            else:
                                if self.contract_id.analytic_account_id.isdepartment:
                                    debit_account_id = line.salary_rule_id.account_debit.id
                                    credit_account_id = line.salary_rule_id.account_credit.id
                                else:
                                    debit_account_id = line.salary_rule_id.project_account_debit.id
                                    credit_account_id = line.salary_rule_id.project_account_credit.id
                            if line.category_id.code in ('DED', 'GOSI'):
                                adjust_debit = (0, 0, {
                                    'name': slip.employee_id.name or '/ ' + line.names,
                                    'partner_id': slip.employee_id.address_home_id.id,
                                    'account_id': debit_account_id,
                                    'journal_id': slip.company_id.accrual_journal.id,
                                    'analytic_account_id': self.contract_id.analytic_account_id.id or False,
                                    'date': self.date_to,
                                    'credit': round(abs(amount), 2),
                                    'debit': 0.0,
                                })
                                total_debit -= round(abs(amount), 2)
                                line_ids.append(adjust_debit)
                            else:
                                adjust_debit = (0, 0, {
                                    'name': slip.employee_id.name or '/ ' + line.names,
                                    'partner_id': slip.employee_id.address_home_id.id,
                                    'account_id': debit_account_id,
                                    'journal_id': slip.company_id.accrual_journal.id,
                                    'analytic_account_id': self.contract_id.analytic_account_id.id or False,
                                    'date': self.date_to,
                                    # 'debit': round(abs(amount), 2),
                                    # 'credit': 0.0,
                                    'debit': amount > 0.0 and round(amount, 2) or 0.0,
                                    'credit': amount < 0.0 and -round(amount, 2) or 0.0,
                                })
                                total_debit += round(amount, 2)
                                line_ids.append(adjust_debit)
                    if line.code == 'NET':
                        debit_account_id = line.salary_rule_id.account_debit.id
                        credit_account_id = line.salary_rule_id.account_credit.id
                        amount = slip.credit_note and -line.total or line.total
                        if credit_account_id:
                            credit_line = (0, 0, {
                                'name': line.name,
                                'partner_id': slip.employee_id.address_home_id.id,
                                'account_id': credit_account_id,
                                'journal_id': slip.journal_id.id,
                                'date': date,
                                'debit': 0.0,  # amount < 0.0 and -amount or 0.0,
                                'credit': total_debit,#round(amount, 2),
                                'analytic_account_id': line.salary_rule_id.analytic_account_id.id,
                                'tax_line_id': line.salary_rule_id.account_tax_id.id,
                            })
                            line_ids.append(credit_line)
                            credit_sum += credit_line[2]['credit'] - credit_line[2]['debit']

                print(line_ids)
                move_dict['line_ids'] = line_ids
                move = self.env['account.move'].create(move_dict)
                slip.write({'move_id': move.id, 'date': date})
                move.post()
                # self.hr_accrual_entry(self.employee_id, self.date_from, self.date_to)
            for line in slip.timesheet_ids:
                line.with_context(skip_warning=True).write({'is_payroll_paid': True, 'custom_payslip_id': slip.id})
                # Gosi Employee Pay
        return self.write({'state': 'done'})
        # except Exception:
        #      print('Error')

    def check_installments_pay(self):
        slip_line_obj = self.env['hr.payslip.line']
        loan_obj = self.env['hr.loan']
        rule_obj = self.env['hr.salary.rule']
        skip_installment_obj = self.env['hr.skip.installment']
        for payslip in self:
            if not payslip.contract_id:
                raise UserError(_("Please enter Employee contract first."))
            loan_ids = loan_obj.search(['|', '&', ('start_date', '>=', payslip.date_from),
                                        ('start_date', '<=', payslip.date_to),
                                        ('start_date', '<=', payslip.date_from),
                                        ('employee_id', '=', payslip.employee_id.id),
                                        ('state', '=', 'approve')])
            rule_ids = rule_obj.search([('code', '=', 'LOAN')])
            if rule_ids:
                rule = rule_ids[0]
                oids = slip_line_obj.search([('slip_id', '=', payslip.id), ('code', '=', 'LOAN')])
                if oids:
                    oids.unlink()
                for loan in loan_ids:
                    skip_installment_ids = skip_installment_obj.search([('loan_id','=',loan.id),('state','=','approve'),('date','>=',payslip.date_from),('date','<=',payslip.date_to)])
                    if not skip_installment_ids:
                        slip_line_data = {
                            'slip_id': payslip.id,
                            'salary_rule_id': rule.id,
                            'contract_id': payslip.contract_id.id,
                            'name': loan.name,
                            'code': 'LOAN' + str(loan.id),
                            'category_id': rule.category_id.id,
                            'sequence': rule.sequence + loan.id,
                            'appears_on_payslip': rule.appears_on_payslip,
                            'condition_select': rule.condition_select,
                            'condition_python': rule.condition_python,
                            'condition_range': rule.condition_range,
                            'condition_range_min': rule.condition_range_min,
                            'condition_range_max': rule.condition_range_max,
                            'amount_select': rule.amount_select,
                            'amount_fix': rule.amount_fix,
                            'amount_python_compute': rule.amount_python_compute,
                            'amount_percentage': rule.amount_percentage,
                            'amount_percentage_base': rule.amount_percentage_base,
                            'register_id': rule.register_id.id,
                            'salary_type': rule.type.id,
                            'amount': -(loan.deduction_amount),
                            'employee_id': payslip.employee_id.id,
                        }
                        if abs(slip_line_data['amount']) > loan.amount_to_pay:
                            slip_line_data.update({'amount': -(loan.amount_to_pay)})
                        slip_line_obj.create(slip_line_data)
                        net_ids = slip_line_obj.search([('slip_id', '=', payslip.id), ('code', '=', 'NET')])
                        if net_ids:
                            net_record = net_ids[0]
                            net_ids.write({'amount': net_record.amount + slip_line_data['amount']})
        return True

    # def compute_sheet_ahcec(self):
    #     for payslip in self:
    #         _logger.critical('========= COMPUTE SHEET AHCEC ============')
    #         number = payslip.number or self.env['ir.sequence'].next_by_code('salary.slip')
    #         # delete old payslip lines
    #         # payslip.line_ids.unlink()
    #
    #         payslip.line_ids = [(5,0,0)]
    #
    #         # set the list of contract for which the rules have to be applied
    #         # if we don't give the contract, then the rules to apply should be for all current contracts of the employee
    #         contract_ids = payslip.contract_id.ids or \
    #                        self.get_contract(payslip.employee_id, payslip.date_from, payslip.date_to)
    #         lines = [(0, 0, line) for line in self._get_payslip_lines_ahcec(contract_ids, payslip.id)]
    #         payslip.write({'line_ids': lines, 'number': number})
    #         # payslip._get_work_type_salary(payslip, payslip.employee_id, payslip.date_from, payslip.date_to)
    #         loan_ids = self.env['hr.loan'].sudo().search(['|', '&', ('start_date', '>=', payslip.date_from),
    #                                     ('start_date', '<=', payslip.date_to),
    #                                     ('start_date', '<=', payslip.date_from),
    #                                     ('employee_id', '=', payslip.employee_id.id),
    #                                     ('state', '=', 'approve')])
    #         _logger.critical('===== ----- ======')
    #         if loan_ids:
    #             payslip.check_installments_pay()
    #             _logger.critical('====== INSIDE if loan_ids =======')
    #         other_ids = self.env['other.hr.payslip'].sudo().search([('date', '>=', payslip.date_from),
    #                                       ('date', '<=', payslip.date_to),
    #                                       ('employee_id', '=', payslip.employee_id.id),
    #                                       ('state', '=', 'done')])
    #         if other_ids:
    #             payslip.check_other_allowance_new()
    #             _logger.critical('====== INSIDE if other_ids =======')
    #         _logger.critical('===== ****** =====')
    #         total_amount = sum(payslip.line_ids.filtered(lambda line: line.category_id.code == 'ALW').mapped('amount'))
    #         basic = sum(payslip.line_ids.filtered(lambda line: line.category_id.code == 'BASIC').mapped('amount'))
    #         payslip.vacation_pay = vacation_pay = 0
    #         if payslip.month_days - payslip.leave_days > 0:
    #             payslip.vacation_pay = vacation_pay = ((basic + total_amount) / (
    #                     payslip.month_days - payslip.leave_days)) * payslip.annual_leaves
    #
    #         if payslip.vacation_pay:
    #             slip_line_obj = self.env['hr.payslip.line']
    #             WORTH_PAY_IDS = slip_line_obj.sudo().search([('slip_id', '=', payslip.id), ('code', '=', 'WORTH_PAY')])
    #             VAC_PAY_IDS = slip_line_obj.sudo().search([('slip_id', '=', payslip.id), ('code', '=', 'VAC_PAY')])
    #             if VAC_PAY_IDS:
    #                 VAC_PAY_IDS.write({'amount': vacation_pay})
    #             if WORTH_PAY_IDS:
    #                 WORTH_PAY_record = WORTH_PAY_IDS[0]
    #                 WORTH_PAY_IDS.write({'amount': basic - vacation_pay})
    #     return True

    # @api.model
    # def _get_payslip_lines_ahcec(self, contract_ids, payslip_id):
    #     def _sum_salary_rule_category(localdict, category, amount):
    #         if category.parent_id:
    #             localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
    #         localdict['categories'].dict[category.code] = category.code in localdict['categories'].dict and \
    #                                                       localdict['categories'].dict[category.code] + amount or amount
    #         return localdict
    #
    #     class BrowsableObject(object):
    #         def __init__(self, employee_id, dict, env):
    #             self.employee_id = employee_id
    #             self.dict = dict
    #             self.env = env
    #
    #         def __getattr__(self, attr):
    #             return attr in self.dict and self.dict.__getitem__(attr) or 0.0
    #
    #     class InputLine(BrowsableObject):
    #         """a class that will be used into the python code, mainly for usability purposes"""
    #
    #         def sum(self, code, from_date, to_date=None):
    #             if to_date is None:
    #                 to_date = fields.Date.today()
    #             self.env.cr.execute("""
    #                     SELECT sum(amount) as sum
    #                     FROM hr_payslip as hp, hr_payslip_input as pi
    #                     WHERE hp.employee_id = %s AND hp.state = 'done'
    #                     AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
    #                                 (self.employee_id, from_date, to_date, code))
    #             return self.env.cr.fetchone()[0] or 0.0
    #
    #     class WorkedDays(BrowsableObject):
    #         """a class that will be used into the python code, mainly for usability purposes"""
    #
    #         def _sum(self, code, from_date, to_date=None):
    #             if to_date is None:
    #                 to_date = fields.Date.today()
    #             self.env.cr.execute("""
    #                     SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours
    #                     FROM hr_payslip as hp, hr_payslip_worked_days as pi
    #                     WHERE hp.employee_id = %s AND hp.state = 'done'
    #                     AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
    #                                 (self.employee_id, from_date, to_date, code))
    #             return self.env.cr.fetchone()
    #
    #         def sum(self, code, from_date, to_date=None):
    #             res = self._sum(code, from_date, to_date)
    #             return res and res[0] or 0.0
    #
    #         def sum_hours(self, code, from_date, to_date=None):
    #             res = self._sum(code, from_date, to_date)
    #             return res and res[1] or 0.0
    #
    #     class Payslips(BrowsableObject):
    #         """a class that will be used into the python code, mainly for usability purposes"""
    #
    #         def sum(self, code, from_date, to_date=None):
    #             if to_date is None:
    #                 to_date = fields.Date.today()
    #             self.env.cr.execute("""SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)
    #                             FROM hr_payslip as hp, hr_payslip_line as pl
    #                             WHERE hp.employee_id = %s AND hp.state = 'done'
    #                             AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s""",
    #                                 (self.employee_id, from_date, to_date, code))
    #             res = self.env.cr.fetchone()
    #             return res and res[0] or 0.0
    #
    #     # we keep a dict with the result because a value can be overwritten by another rule with the same code
    #     result_dict = {}
    #     rules_dict = {}
    #     worked_days_dict = {}
    #     inputs_dict = {}
    #     blacklist = []
    #     payslip = self.env['hr.payslip'].browse(payslip_id)
    #     for worked_days_line in payslip.worked_days_line_ids:
    #         worked_days_dict[worked_days_line.code] = worked_days_line
    #     for input_line in payslip.input_line_ids:
    #         inputs_dict[input_line.code] = input_line
    #
    #     categories = BrowsableObject(payslip.employee_id.id, {}, self.env)
    #     inputs = InputLine(payslip.employee_id.id, inputs_dict, self.env)
    #     worked_days = WorkedDays(payslip.employee_id.id, worked_days_dict, self.env)
    #     payslips = Payslips(payslip.employee_id.id, payslip, self.env)
    #     rules = BrowsableObject(payslip.employee_id.id, rules_dict, self.env)
    #
    #     baselocaldict = {'categories': categories, 'rules': rules, 'payslip': payslips, 'worked_days': worked_days,
    #                      'inputs': inputs}
    #     # get the ids of the structures on the contracts and their parent id as well
    #     contracts = self.env['hr.contract'].browse(contract_ids)
    #     # if len(contracts) == 1 and payslip.struct_id:
    #     #     structure_ids = list(set(payslip.struct_id._get_parent_structure().ids))
    #     # else:
    #     #     structure_ids = contracts.get_all_structures()
    #     # get the rules of the structure and thier children
    #     # rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
    #     # run the rules by sequence
    #     # sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
    #     # sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)
    #
    #     # for contract in contracts:
    #     #
    #     #     employee = contract.employee_id
    #     #     localdict = dict(baselocaldict, employee=employee, contract=contract)
    #     #     for rule in sorted_rules:
    #     #         key = rule.code + '-' + str(contract.id)
    #     #         localdict['result'] = None
    #     #         localdict['result_qty'] = 1.0
    #     #         localdict['result_rate'] = 100
    #     #         # check if the rule can be applied
    #     #         if rule._satisfy_condition(localdict) and rule.id not in blacklist:
    #     #             # compute the amount of the rule
    #     #             amount, qty, rate = rule._compute_rule(localdict)
    #     #             # check if there is already a rule computed with that code
    #     #             previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
    #     #             # set/overwrite the amount computed for this rule in the localdict
    #     #             tot_rule = amount * qty * rate / 100.0
    #     #             localdict[rule.code] = tot_rule
    #     #             rules_dict[rule.code] = rule
    #     #             # sum the amount for its salary category
    #     #             localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
    #     #             # create/overwrite the rule in the temporary results
    #     #             result_dict[key] = {
    #     #                 'salary_rule_id': rule.id,
    #     #                 'contract_id': contract.id,
    #     #                 'name': rule.name,
    #     #                 'code': rule.code,
    #     #                 'category_id': rule.category_id.id,
    #     #                 'sequence': rule.sequence,
    #     #                 'appears_on_payslip': rule.appears_on_payslip,
    #     #                 'condition_select': rule.condition_select,
    #     #                 'condition_python': rule.condition_python,
    #     #                 'condition_range': rule.condition_range,
    #     #                 'condition_range_min': rule.condition_range_min,
    #     #                 'condition_range_max': rule.condition_range_max,
    #     #                 'amount_select': rule.amount_select,
    #     #                 'amount_fix': rule.amount_fix,
    #     #                 'amount_python_compute': rule.amount_python_compute,
    #     #                 'amount_percentage': rule.amount_percentage,
    #     #                 'amount_percentage_base': rule.amount_percentage_base,
    #     #                 'register_id': rule.register_id.id,
    #     #                 'amount': amount,
    #     #                 'salary_type': rule.type.id,
    #     #                 'employee_id': contract.employee_id.id,
    #     #                 'quantity': qty,
    #     #                 'rate': rate,
    #     #             }
    #     #         else:
    #     #             # blacklist this rule and its children
    #     #             blacklist += [id for id, seq in rule._recursive_search_of_rules()]
    #
    #     return list(result_dict.values())

    def check_other_allowance_new(self):
        slip_line_obj = self.env['hr.payslip.line']
        other_obj = self.env['other.hr.payslip']
        rule_obj = self.env['hr.salary.rule']
        skip_installment_obj = self.env['hr.skip.installment']
        for payslip in self:
            if not payslip.contract_id:
                raise UserError(_("Please enter Employee contract first."))
            other_ids = other_obj.search([('date', '>=', payslip.date_from),
                                          ('date', '<=', payslip.date_to),
                                          ('employee_id', '=', payslip.employee_id.id),
                                          ('state', '=', 'done')])
            oids = slip_line_obj.search(
                [('slip_id', '=', payslip.id), ('code', 'in', ('ADDITIONAL_ALW', 'ADDITIONAL_DED'))])
            if oids:
                oids.unlink()
                # individual.inverse_name = False
            for other in other_ids:
                amount = other.amount
                rule_ids = rule_obj.search([('code', '=', 'ADDITIONAL_ALW')])
                if other.operation_type == 'deduction':
                    rule_ids = rule_obj.search([('code', '=', 'ADDITIONAL_DED')])
                    amount = -(amount)
                if rule_ids:
                    rule = rule_ids[0]
                    slip_line_data = {
                        'slip_id': payslip.id,
                        'salary_rule_id': rule.id,
                        'contract_id': payslip.contract_id.id,
                        'name': other.salary_rule.name,
                        'code': 'ADDITIONAL',
                        'category_id': rule.category_id.id,
                        'sequence': rule.sequence,
                        'appears_on_payslip': rule.appears_on_payslip,
                        'condition_select': rule.condition_select,
                        'condition_python': rule.condition_python,
                        'condition_range': rule.condition_range,
                        'condition_range_min': rule.condition_range_min,
                        'condition_range_max': rule.condition_range_max,
                        'amount_select': rule.amount_select,
                        'amount_fix': rule.amount_fix,
                        'amount_python_compute': rule.amount_python_compute,
                        'amount_percentage': rule.amount_percentage,
                        'amount_percentage_base': rule.amount_percentage_base,
                        'register_id': rule.register_id.id,
                        'dummy_account': other.account_id.id,
                        'salary_type': other.salary_rule.type.id,
                        'amount': amount,
                        'employee_id': payslip.employee_id.id,
                    }

                    slip_line_obj.create(slip_line_data)
                    gross_ids = slip_line_obj.search([('slip_id', '=', payslip.id), ('code', '=', 'GROSS')])
                    net_ids = slip_line_obj.search([('slip_id', '=', payslip.id), ('code', '=', 'NET')])
                    if net_ids:
                        net_record = net_ids[0]
                        net_ids.write({'amount': net_record.amount + slip_line_data['amount']})
                    if gross_ids:
                        gross_record = gross_ids[0]
                        if slip_line_data['amount'] > 0:
                            gross_ids.write({'amount': gross_record.amount + slip_line_data['amount']})

        return True
# class HrPayrollLine(models.Model):
#     _inherit = 'hr.payslip'
#
#     vacation_pay_new = fields.Float('Vacation Pay')

# class MultiPaySlipWiz(models.TransientModel):
#     _inherit = 'multi.payslip.wizard'
#
#     def multi_payslip(self):
#         payslip_ids = self.env['hr.payslip']. \
#             browse(self._context.get('active_ids'))
#         for payslip in payslip_ids:
#             if payslip.state == 'draft':
#                 payslip.action_payslip_done_new()


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def confirm_all_sheet(self):
        for line in self.slip_ids:
            line.action_payslip_done_new()

    def compute_sheet_all(self):
        for line in self.slip_ids:
            line.compute_sheet_ahcec()

        return True

