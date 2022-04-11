# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)


class HRContract(models.Model):
    _name = 'hr.contract'
    _inherit = ['mail.thread', 'hr.contract']

    mobile = fields.Boolean('Eligible for Mobile Allowance')
    mobile_allowance = fields.Float('Mobile Allowance', help="Mobile Allowance")
    signon_bonus = fields.Boolean('Eligible for Bonus')
    signon_bonus_amount = fields.Float('Bonus Amount', digits=(16, 2), help="Mention the Sign on Bonus amount.")
    period_ids = fields.Many2many('year.period', string='Month(s)',
                                  help='Specify month(s) in which the sign on bonus will be distributed. Bonus will be distributed in Bonus Amount/Number of Month(s).')
    # iron_allowance = fields.Float('Iron Allowance', digits=(16, 2), help="Mention the iron allowance.")
    # is_iron_allowance = fields.Boolean('Allow Iron Allowance')
    notice_start_date = fields.Date('Notice Start Date', readonly=True)
    notice_end_date = fields.Date('Notice End Date', readonly=True)
    is_leaving = fields.Boolean('Leaving Notice')
    # is_notify = fields.Boolean('is notify ? ')
    # notify_date = fields.Date("Notify Date", compute='_get_notify_date')
    basic = fields.Float('Basic', compute='_get_amount', help='Basic Salary of Employee(value after gross/1.35)')
    is_HRA = fields.Boolean(string="Eligible for HRA")
    HRA = fields.Float(string='House Rent Allowance')
    is_TA = fields.Boolean(string="Eligible for TA")
    TA = fields.Float(string='Transport Allowance')
    is_cda = fields.Boolean(string="Eligible for C & SD Allowance")
    cda = fields.Float(string='C & SD Allowance')  # Consumables and Spending Differentials
    is_other_allow = fields.Boolean(string="Eligible for Other Allowance")
    other_allow = fields.Float(string='Other Allowance')
    is_shift_allow = fields.Boolean(string="Eligible for Shift Allowance")
    shift_allow = fields.Float(string='Shift Allowance')
    is_remote_allow = fields.Boolean(string="Eligible for Remote Area Allowance")
    remote_allow = fields.Float(string='Remote Area Allowance')
    total_salary = fields.Float(string='Total Salary', compute='_get_total')
    ot_rate = fields.Float(string='OT Rate', compute='_get_amount')
    hr_rate = fields.Float(string='Hourly Rate', compute='_get_amount')
    # gosi_type = fields.Selection([('manual', 'Manual'), ('Auto', 'Auto')],required=True)
    gosi_employee_pay_manual = fields.Float(string='Gosi Employee Pay (Manual)')
    gosi_company_pay_manual = fields.Float(string='Gosi Company Pay (Manual)')
    gosi_employee_pay = fields.Float(string='Gosi Employee Pay', compute='_get_gosi')
    gosi_company_pay = fields.Float(string='Gosi Company Pay', compute='_get_gosi')
    gosi_total_pay = fields.Float(string='Gosi Total', compute='_get_gosi')
    gosi_eligible = fields.Boolean(string='Gosi Eligible', default=True)
    is_insurance = fields.Boolean(string='Eligible for Insurance')
    insurance_id = fields.Many2one('insurance.details', string='Insurance Details')
    insurance_cost = fields.Float(string='Insurance Cost')
    is_eos_amount = fields.Boolean(string='Eligible for STB')
    today = fields.Date('Today', readonly=True, compute='_get_eos')
    total_days = fields.Integer('Total Days', compute='_get_eos')
    eos_amount = fields.Float(string='STB As of Today', compute='_get_eos')
    eos_accrual_move_id = fields.Many2one('account.move', string='Accrual Move')
    is_vacation = fields.Boolean(string='Eligible for Vacation')
    # ********************************
    # employee_id = fields.Many2one('hr.employee', string='Employee')
    # ********************************
    # remaining_leaves = fields.Float(string='Remaining Leaves', related='employee_id.remaining_leaves')
    remaining_leaves = fields.Float(string='Remaining Leaves')
    vacation = fields.Float('Vacation Salary', compute='_get_vacation')
    is_sce = fields.Boolean(string='Eligible for SCE or Others')
    sce = fields.Float('SCE Fee')
    is_other_insurance = fields.Boolean(string='Eligible for Other Insurance')
    other_insurance = fields.Float('Other Insurance Cost')
    mobilization_fee = fields.Float('Mobilization Fee')
    residency_cost = fields.Float('Residency Cost')
    yearly_indirect_cost = fields.Float('Yearly Indirect Cost', compute='_get_cost')
    monthly_indirect_cost = fields.Float('Monthly Indirect Cost', compute='_get_cost')
    total_monthly_cost = fields.Float('Total Monthly Cost', compute='_get_cost')
    total_yearly_cost = fields.Float('Total Yearly Cost', compute='_get_cost')
    ticket_total = fields.Float('Ticket Total', compute='_get_cost')

    @api.model
    def create(self, values):
        """
            create a new record
        """
        if values.get('employee_id', False):
            employee = self.env['hr.employee'].browse(values['employee_id'])
            values.update({'job_id': employee.job_id.id or False})
            contracts = employee.get_active_contracts(date=fields.Date.today())
            # for cont in contracts:
            #     if cont.state in ('draft','open','pending'):
            #         raise UserError(_('Please close the active contracts of %s') % employee.name)
        return super(HRContract, self).create(values)

    def write(self, values):
        """
            update an existing record
        """
        if values.get('employee_id', False):
            employee = self.env['hr.employee'].browse(values['employee_id'])
            values.update({'job_id': employee.job_id.id or False})
        return super(HRContract, self).write(values)

    # @api.depends('date_end')
    # def _get_notify_date(self):
    #     self.notify_date = False
    #     if self.date_end:
    #         date_end = fields.Datetime.from_string(self.date_end)
    #         self.notify_date = date_end - relativedelta(months=+2)

    @api.depends('total_salary', 'insurance_cost', 'eos_amount', 'vacation', 'mobilization_fee',
                 'residency_cost', 'signon_bonus_amount')
    def _get_cost(self):
        for contract in self:
            contract.yearly_indirect_cost = contract.insurance_cost + contract.ticket_total + contract.eos_amount + \
                                            contract.vacation + contract.mobilization_fee + contract.residency_cost + \
                                            contract.signon_bonus_amount
            contract.monthly_indirect_cost = contract.yearly_indirect_cost / 12
            contract.total_monthly_cost = contract.monthly_indirect_cost + contract.total_salary
            contract.total_yearly_cost = contract.total_monthly_cost * 12

    @api.depends('wage', 'mobile_allowance', 'signon_bonus_amount', 'HRA', 'TA', 'cda', 'other_allow', 'shift_allow',
                 'remote_allow')
    def _get_total(self):
        for contract in self:
            contract.total_salary = contract.wage + \
                                    contract.mobile_allowance + \
                                    contract.signon_bonus_amount + \
                                    contract.HRA + contract.TA + \
                                    contract.cda + \
                                    contract.other_allow + \
                                    contract.shift_allow + \
                                    contract.remote_allow

    @api.depends('is_vacation', 'total_salary')
    def _get_vacation(self):
        for contract in self:
            if contract.is_vacation:
                contract.vacation = (contract.total_salary / 30) * contract.remaining_leaves
            else:
                contract.vacation = 0

    @api.depends('wage', 'HRA')
    def _get_gosi(self):
        for contract in self:
            if contract.employee_id.country_id and contract.employee_id.country_id.code == 'SA':
                if (contract.wage + contract.HRA) > 45000:
                    contract.gosi_employee_pay = 45000 * 0.1
                    contract.gosi_company_pay = 45000 * 0.12
                else:
                    contract.gosi_employee_pay = (contract.wage + contract.HRA) * 0.1
                    contract.gosi_company_pay = (contract.wage + contract.HRA) * 0.12

            elif contract.employee_id.country_id and contract.employee_id.country_id.code == 'BH':
                if (contract.wage + contract.HRA) > 40000:
                    contract.gosi_employee_pay = 40000 * 0.06
                    contract.gosi_company_pay = 40000 * 0.1
                else:
                    contract.gosi_employee_pay = (contract.wage + contract.HRA) * 0.06
                    contract.gosi_company_pay = (contract.wage + contract.HRA) * 0.11
            else:
                if (contract.wage + contract.HRA) > 45000:
                    contract.gosi_employee_pay = 0
                    contract.gosi_company_pay = 45000 * 0.02
                else:
                    contract.gosi_employee_pay = 0
                    contract.gosi_company_pay = (contract.wage + contract.HRA) * 0.02

            contract.gosi_total_pay = contract.gosi_employee_pay + contract.gosi_company_pay

    # s #         contract.gosi_company_pay_manual = contract.gosi_company_pay
    @api.depends()
    def _get_eos(self):
        for contract in self:
            if contract.employee_id.joining_date:
                # join_date = datetime.strptime(contract.employee_id.joining_date, DEFAULT_SERVER_DATE_FORMAT)
                join_date = datetime.strptime(str(contract.employee_id.joining_date), DEFAULT_SERVER_DATE_FORMAT)
                contract.today = fields.Date.today()
                # leave_date = datetime.strptime(contract.today, DEFAULT_SERVER_DATE_FORMAT)
                leave_date = datetime.strptime(str(contract.today), DEFAULT_SERVER_DATE_FORMAT)
                diff = relativedelta(leave_date, join_date)
                duration_days = diff.days
                duration_months = diff.months
                duration_years = diff.years
                from_date = datetime.strptime(str(contract.employee_id.joining_date), '%Y-%m-%d')
                start = datetime.date(from_date)
                end_date = datetime.strptime(str(contract.today), '%Y-%m-%d')
                end = datetime.date(end_date)
                days = abs(end - start).days + 1
                contract.total_days = days
                logging.info('duration_days : %s' + str(days))
                # if duration_years >= 2 and duration_years < 5:
                # if duration_years < 5:
                #     contract.eos_amount = ((contract.total_salary / 2) * duration_years) + (((contract.total_salary / 2) / 12) * duration_months) + (
                #                 (((contract.total_salary / 2) / 12) / 30) * duration_days)
                # elif duration_years >= 5 and duration_years < 10:
                #     contract.eos_amount = ((contract.total_salary / 2) * duration_years) + ((contract.total_salary / 12) * duration_months) + (
                #                 ((contract.total_salary / 12) / 30) * duration_days)
                # elif duration_years >= 10:
                #     contract.eos_amount = ((contract.total_salary / 2) * 5) + (contract.total_salary * (duration_years - 5)) + ((contract.total_salary / 12) * duration_months) + (
                #                 (contract.total_salary / 365) * duration_days)
                if days < 1825:
                    contract.eos_amount = (days * (contract.total_salary / 2) / 365)
                else:
                    contract.eos_amount = (1825 * (contract.total_salary / 2) / 365) + (
                            ((days - 1825) * contract.total_salary) / 365)

    @api.depends('wage')
    def _get_amount(self):
        for contract in self:
            # if contract.wage > 0:
            # contract.basic = contract.wage / 1.35
            contract.basic = contract.wage
            # contract.HRA = contract.basic * 0.25
            # contract.TA = contract.basic * 0.1
            contract.hr_rate = ((contract.basic * 12) / 2920)
            contract.ot_rate = ((contract.basic * 12) / 2920) * 1.5

    @api.onchange('employee_id')
    def onchange_employee(self):
        self.job_id = False
        self.mobile_allowance = 0.0
        if self.employee_id:
            employee = self.env['hr.employee'].browse(self.employee_id.id)
            if employee.grade_id:
                self.mobile_allowance = employee.grade_id.mobile_allowance
            self.job_id = employee.job_id.id or False
            self.department_id = employee.department_id.id or False

    @api.onchange('insurance_id')
    def onchance_insurance_id(self):
        for contract in self:
            contract.insurance_cost = contract.insurance_id.insurance_amount

    @api.onchange('mobile', 'employee_id')
    def onchange_mobile(self):
        self.mobile_allowance = 0.0
        if self.mobile and self.employee_id:
            employee = self.env['hr.employee'].browse(self.employee_id.id)
            if employee.grade_id:
                self.mobile_allowance = employee.grade_id.mobile_allowance

    @api.model
    def run_scheduler(self):
        contract_ids = self.search([('state', 'in', ['draft', 'open'])])
        try:
            template_id = self.env.ref('hr_contract.email_template_hr_contract_notify')
        except ValueError:
            template_id = False
        hr_groups_config_obj = self.env['hr.groups.configuration']
        for contract in contract_ids:
            if contract.date_end:
                if str(datetime.now().date()) == str((datetime.strptime(contract.date_end,
                                                                        DEFAULT_SERVER_DATE_FORMAT) - relativedelta(
                    months=+2)).date()):
                    hr_groups_config_ids = hr_groups_config_obj.search(
                        [('branch_id', '=', contract.employee_id.branch_id.id or False), ('hr_ids', '!=', False)])
                    hr_groups_ids = hr_groups_config_ids and hr_groups_config_obj.browse(hr_groups_config_ids.ids)[0]
                    user_ids = hr_groups_ids and [item.user_id.id for item in hr_groups_ids.hr_ids if
                                                  item.user_id] or []
                    email_to = ''
                    res_users_obj = self.env['res.users']
                    for user_id in res_users_obj.browse(user_ids):
                        if user_id.email:
                            email_to = email_to and email_to + ',' + user_id.email or email_to + user_id.email
                    template_id.write({'email_to': email_to, 'reply_to': email_to, 'auto_delete': False})
                    template_id.send_mail(contract.id, force_send=True)
                    contract.write({'state': 'pending'})
                elif datetime.now().date() == datetime.strptime(contract.date_end, DEFAULT_SERVER_DATE_FORMAT).date():
                    contract.write({'state': 'close'})
        return True


class HRGrade(models.Model):
    _inherit = "hr.grade"

    mobile_allowance = fields.Float('Mobile Allowance', help="Mobile Allowance")
