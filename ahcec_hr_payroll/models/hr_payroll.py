# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
from odoo import api, models, fields, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError
from datetime import time as datetime_time
import logging
_logger = logging.getLogger(__name__)


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    dummy_account = fields.Many2one('account.account', 'Dummy Account',
                                            domain=[('deprecated', '=', False)])
    type = fields.Many2one(related='salary_rule_id.type', string='Type')
    other_type = fields.Many2one('hr.other.salary.rule', string='Type')


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def compute_all_sheet(self):
        for line in self.slip_ids:
            # clause_1 = ['&', ('date_end', '<=', self.date_end), ('date_end', '>=', self.date_start)]
            # clause_2 = ['&', ('date_start', '<=', self.date_end), ('date_start', '>=', self.date_start)]
            # clause_3 = ['&', ('date_start', '<=', self.date_start), '|', ('date_end', '=', False),
            #             ('date_end', '>=', self.date_end)]
            # clause_final = [('employee_id', '=', line.employee_id.id), ('state', '=', 'open')]
            # contracts = self.env['hr.contract'].search([('employee_id', '=', line.employee_id.id), ('state', '=', 'open')],limit=1).id
            #
            # print('########### :: %s',contracts)
            #
            # line.onchange_employee_id(self.date_start, self.date_end,line.employee_id.id,contracts)
            print('Employee Code :',line.employee_id.employee_code)
            line.compute_sheet()

        return True


class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    payment_days = fields.Float(compute='_get_payment_days', string='Payment Day(s)')
    month_days = fields.Float(compute='_get_payment_days', string='Month Day(s)')
    leave_days = fields.Float(compute='_get_payment_days', string='Leave Day(s)')
    annual_leaves = fields.Float(compute='_get_payment_days', string='Annual Day(s)')
    vacation_pay = fields.Float(string='Vacation Pay')
    department_id = fields.Many2one('hr.department', string="Department", related='employee_id.department_id',
                                    store=True)

    def _get_payment_days(self):
        for line in self:
            # day_from = datetime.combine(fields.Date.from_string(line.date_from), datetime_time.min)
            # day_to = datetime.combine(fields.Date.from_string(line.date_to), datetime_time.max)
            # leave_days = line.employee_id.get_leaves_day_count(day_from, day_to,
            #                                                        calendar=line.employee_id.resource_calendar_id)
            leave_days = sum(line.worked_days_line_ids.filtered(lambda record: record.code == 'unpaid_leave').mapped(
                'number_of_days'))
            _logger.critical('===================')
            _logger.critical(leave_days)
            annual_leaves = sum(line.worked_days_line_ids.filtered(
                lambda record: record.code in ('annual_leave', 'sick_leaves')).mapped('number_of_days'))
            day_from = datetime.strptime(str(line.date_from), DEFAULT_SERVER_DATE_FORMAT)
            day_to = datetime.strptime(str(line.date_to), DEFAULT_SERVER_DATE_FORMAT)
            nb_of_days = (day_to - day_from).days + 1
            line.month_days = nb_of_days
            line.leave_days = leave_days
            line.annual_leaves = annual_leaves
            month = datetime.strptime(str(line.date_from), DEFAULT_SERVER_DATE_FORMAT).month
            # if nb_of_days>30 or month==2 and nb_of_days==28: #If month is February or days are greater than 28 then payment days set to 30
            #     nb_of_days = 30
            _logger.critical('********************')
            line.payment_days = nb_of_days - leave_days


    # @api.onchange('month_days', 'annual_leaves', 'line_ids')
    # def onchange_vacation_pay(self):
    #     for line in self:
    #         total_amount = sum(line.line_ids.filtered(lambda line: line.category_id.code == 'ALW').mapped('amount'))
    #         basic = sum(line.line_ids.filtered(lambda line: line.category_id.code == 'BASIC').mapped('amount'))
    #         line.vacation_pay = ((basic + total_amount) / (line.month_days - line.leave_days)) * line.annual_leaves

    def get_other_allowance_deduction(self, employee_id, date_from, date_to):
        from_date = datetime.strptime(date_from, DEFAULT_SERVER_DATE_FORMAT)
        to_date = datetime.strptime(date_to, DEFAULT_SERVER_DATE_FORMAT)
        new_from_date = from_date + relativedelta(months=-1, day=25)
        last_day = calendar.monthrange(to_date.year, to_date.month)[1]
        new_to_date = to_date + relativedelta(day=24)
        if to_date.day < last_day:
            new_to_date = to_date
        domain = [('employee_id', '=', employee_id.id),
                  ('payslip_id', '=', False), ('state', 'in', ['done']),
                  ('date', '>=', new_from_date), ('date', '<=', new_to_date)]
        other_ids = self.env['other.hr.payslip'].search(domain)
        return other_ids

    # @api.model
    # def _get_payslip_lines(self, contract_ids, payslip_id):
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
    #     if len(contracts) == 1 and payslip.struct_id:
    #         structure_ids = list(set(payslip.struct_id._get_parent_structure().ids))
    #     else:
    #         structure_ids = contracts.get_all_structures()
    #     # get the rules of the structure and thier children
    #     rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
    #     # run the rules by sequence
    #     sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x: x[1])]
    #     sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)
    #
    #     for contract in contracts:
    #         employee = contract.employee_id
    #         localdict = dict(baselocaldict, employee=employee, contract=contract)
    #         for rule in sorted_rules:
    #             key = rule.code + '-' + str(contract.id)
    #             localdict['result'] = None
    #             localdict['result_qty'] = 1.0
    #             localdict['result_rate'] = 100
    #             # check if the rule can be applied
    #             if rule._satisfy_condition(localdict) and rule.id not in blacklist:
    #                 # compute the amount of the rule
    #                 amount, qty, rate = rule._compute_rule(localdict)
    #                 # check if there is already a rule computed with that code
    #                 previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
    #                 # set/overwrite the amount computed for this rule in the localdict
    #                 tot_rule = amount * qty * rate / 100.0
    #                 localdict[rule.code] = tot_rule
    #                 rules_dict[rule.code] = rule
    #                 # sum the amount for its salary category
    #                 localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
    #                 # create/overwrite the rule in the temporary results
    #                 result_dict[key] = {
    #                     'salary_rule_id': rule.id,
    #                     'contract_id': contract.id,
    #                     'name': rule.name,
    #                     'code': rule.code,
    #                     'category_id': rule.category_id.id,
    #                     'sequence': rule.sequence,
    #                     'appears_on_payslip': rule.appears_on_payslip,
    #                     'condition_select': rule.condition_select,
    #                     'condition_python': rule.condition_python,
    #                     'condition_range': rule.condition_range,
    #                     'condition_range_min': rule.condition_range_min,
    #                     'condition_range_max': rule.condition_range_max,
    #                     'amount_select': rule.amount_select,
    #                     'amount_fix': rule.amount_fix,
    #                     'amount_python_compute': rule.amount_python_compute,
    #                     'amount_percentage': rule.amount_percentage,
    #                     'amount_percentage_base': rule.amount_percentage_base,
    #                     'register_id': rule.register_id.id,
    #                     'amount': amount,
    #                     # 'type': rule.type.id,
    #                     'employee_id': contract.employee_id.id,
    #                     'quantity': qty,
    #                     'rate': rate,
    #                 }
    #             else:
    #                 # blacklist this rule and its children
    #                 blacklist += [id for id, seq in rule._recursive_search_of_rules()]
    #
    #     return list(result_dict.values())

    # @api.model
    # def get_inputs(self, contract_ids, date_from, date_to):
    #     res = super(HrPayslip, self).get_inputs(contract_ids, date_from, date_to)
    #     alw_no_of_days = alw_no_of_hours = alw_percentage = alw_amt = 0.0
    #     ded_no_of_days = ded_no_of_hours = ded_percentage = ded_amt = 0.0
    #
    #
    #     for contract in contract_ids:
    #         other_ids = self.get_other_allowance_deduction(contract.employee_id, date_from, date_to)
    #         input_deduction_lines = {}
    #         input_allowance_lines = {}
    #         if other_ids:
    #             for other in other_ids:
    #                 if other.operation_type == 'allowance':
    #                     if other.calc_type == 'amount':
    #                         alw_amt += other.amount
    #                         if 'OTHER_ALLOWANCE_AMOUNT' not in input_allowance_lines:
    #                             input_allowance_lines['OTHER_ALLOWANCE_AMOUNT'] = alw_amt
    #                         else:
    #                             input_allowance_lines.update({'OTHER_ALLOWANCE_AMOUNT': alw_amt})
    #                     elif other.calc_type == 'days':
    #                         alw_no_of_days += other.no_of_days
    #                         if 'OTHER_ALLOWANCE_DAYS' not in input_allowance_lines:
    #                             input_allowance_lines['OTHER_ALLOWANCE_DAYS'] = alw_no_of_days
    #                         else:
    #                             input_allowance_lines.update({'OTHER_ALLOWANCE_DAYS': alw_no_of_days})
    #                     elif other.calc_type == 'hours':
    #                         alw_no_of_hours += other.no_of_hours
    #                         if 'OTHER_ALLOWANCE_HOURS' not in input_allowance_lines:
    #                             input_allowance_lines['OTHER_ALLOWANCE_HOURS'] = alw_no_of_hours
    #                         else:
    #                             input_allowance_lines.update({'OTHER_ALLOWANCE_HOURS': alw_no_of_hours})
    #                     elif other.calc_type == 'percentage':
    #                         alw_percentage += other.percentage
    #                         if 'OTHER_ALLOWANCE_PERCENTAGE' not in input_allowance_lines:
    #                             input_allowance_lines['OTHER_ALLOWANCE_PERCENTAGE'] = alw_percentage
    #                         else:
    #                             input_allowance_lines.update({'OTHER_ALLOWANCE_PERCENTAGE': alw_percentage})
    #
    #
    #                 elif other.operation_type == 'deduction':
    #                     name = 'Other Deduction'
    #                     if other.calc_type == 'amount':
    #                         ded_amt += other.amount
    #                         if 'OTHER_DEDUCTION_AMOUNT' not in input_deduction_lines:
    #                             input_deduction_lines['OTHER_DEDUCTION_AMOUNT'] = ded_amt
    #                         else:
    #                             input_deduction_lines.update({'OTHER_DEDUCTION_AMOUNT': ded_amt})
    #                     elif other.calc_type == 'days':
    #                         ded_no_of_days += other.no_of_days
    #                         if 'OTHER_DEDUCTION_DAYS' not in input_deduction_lines:
    #                             input_deduction_lines['OTHER_DEDUCTION_DAYS'] = ded_no_of_days
    #                         else:
    #                             input_deduction_lines.update({'OTHER_DEDUCTION_DAYS': ded_no_of_days})
    #                     elif other.calc_type == 'hours':
    #                         ded_no_of_hours += other.no_of_hours
    #                         if 'OTHER_DEDUCTION_HOURS' not in input_deduction_lines:
    #                             input_deduction_lines['OTHER_DEDUCTION_HOURS'] = ded_no_of_hours
    #                         else:
    #                             input_deduction_lines.update({'OTHER_DEDUCTION_HOURS': ded_no_of_hours})
    #                     elif other.calc_type == 'percentage':
    #                         ded_percentage += other.percentage
    #                         if 'OTHER_DEDUCTION_PERCENTAGE' not in input_deduction_lines:
    #                             input_deduction_lines['OTHER_DEDUCTION_PERCENTAGE'] = ded_percentage
    #                         else:
    #                             input_deduction_lines.update({'OTHER_DEDUCTION_PERCENTAGE': ded_percentage})
    #
    #             for code, amount in input_allowance_lines.items() :
    #                 res.append({
    #                             'name': 'Other Allowance',
    #                             'code': code,
    #                             'amount': amount,
    #                             'contract_id': contract.id,
    #                         })
    #
    #             for code, amount in input_deduction_lines.items() :
    #                 res.append({
    #                             'name': 'Other Deduction',
    #                             'code': code,
    #                             'amount': amount,
    #                             'contract_id': contract.id,
    #                         })
    #
    #     return res

    def check_other_allowance(self):
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
            oids = slip_line_obj.search([('slip_id', '=', payslip.id), ('code', 'in', ('ADDITIONAL_ALW','ADDITIONAL_DED'))])
            if oids:
                oids.unlink()
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
                        'salary_type':other.salary_rule.id,
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

    # def compute_sheet(self):
    #     res = super(HrPayslip, self).compute_sheet()
    #     for payslip in self:
    #         payslip.check_other_allowance()
    #         total_amount = sum(payslip.line_ids.filtered(lambda line: line.category_id.code == 'ALW').mapped('amount'))
    #         basic = sum(payslip.line_ids.filtered(lambda line: line.category_id.code == 'BASIC').mapped('amount'))
    #         payslip.vacation_pay = vacation_pay = 0
    #         if payslip.month_days - payslip.leave_days > 0:
    #             payslip.vacation_pay = vacation_pay = ((basic + total_amount) / (
    #                     payslip.month_days - payslip.leave_days)) * payslip.annual_leaves
    #
    #         if payslip.vacation_pay:
    #             slip_line_obj = self.env['hr.payslip.line']
    #             WORTH_PAY_IDS = slip_line_obj.search([('slip_id', '=', payslip.id), ('code', '=', 'WORTH_PAY')])
    #             VAC_PAY_IDS = slip_line_obj.search([('slip_id', '=', payslip.id), ('code', '=', 'VAC_PAY')])
    #             if VAC_PAY_IDS:
    #                 VAC_PAY_IDS.write({'amount': vacation_pay})
    #             if WORTH_PAY_IDS:
    #                 WORTH_PAY_record = WORTH_PAY_IDS[0]
    #                 WORTH_PAY_IDS.write({'amount': basic - vacation_pay})
    #     return res
