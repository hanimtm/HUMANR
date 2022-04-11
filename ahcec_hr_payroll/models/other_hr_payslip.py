# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import time

class OtherHrPayslip(models.Model):
    _name = 'hr.other.salary.rule'

    name = fields.Char('Name',required=True)
    operation_type = fields.Selection([('allowance', 'Allowance'),
                                       ('deduction', 'Deduction')], string='Type', required=True)
    account_id = fields.Many2one('account.account', 'Account',
                                    domain=[('deprecated', '=', False)])
    type = fields.Many2one('hr.salary.type', string='Type', store=True)

    _sql_constraints = [
        (
        'name_uniq', 'unique(name,account_id)', 'Name and Account is duplicated, Please change'),
    ]

class OtherHrPayslip(models.Model):
    _name = 'other.hr.payslip'
    _inherit = ['mail.thread']
    _description = "Other HR Payslip"

    name = fields.Char(related='employee_id.name')
    amount = fields.Float('Amount')
    no_of_days = fields.Float('No of Days')
    operation_type = fields.Selection([('allowance', 'Allowance'),
                              ('deduction', 'Deduction')], string='Type', default='allowance', required=True)
    calc_type = fields.Selection([('amount', 'By Amount'), ('days', 'By Days'), ('hours', 'By Hours'), ('percentage', 'By Percentage')], string='Calculation Type',
                                 required=True, default='amount')
    country_id = fields.Many2one('res.country', 'Country')
    no_of_hours = fields.Float(string='No of Hours')
    percentage = fields.Float(string='Percentage')
    date = fields.Date('Date', required=True, default=lambda *a: time.strftime('%Y-%m-%d'))
    description = fields.Text('Description', required=True)
    approved_date_to = fields.Date('Approved Date To', copy=False)
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    payslip_id = fields.Many2one('hr.payslip', readonly=True, string='Payslip', copy=False)
    department_id = fields.Many2one('hr.department', readonly=True, string='Department')
    salary_rule = fields.Many2one('hr.other.salary.rule', required=True, string='Salary Rule')
    state = fields.Selection([('draft', 'Draft'),
                              ('done', 'Done')], string='State', default='draft', track_visibility='onchange')
    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.user.company_id)
    account_id = fields.Many2one('account.account', 'Account',
                                 domain=[('deprecated', '=', False)])


    def unlink(self):
        for line in self:
            if line.state in ['done']:
                raise UserError(_('You cannot remove the record which is in %s state!') %(line.state))
        return super(OtherHrPayslip, self).unlink()

    @api.onchange('employee_id')
    def onchange_employee(self):
        self.department_id = False
        if self.employee_id:
            self.department_id = self.employee_id.department_id.id
            self.company_id = self.employee_id.company_id.id

    @api.onchange('salary_rule')
    def onchange_salary_rule(self):
        if self.salary_rule:
            self.operation_type = self.salary_rule.operation_type
            self.account_id = self.salary_rule.account_id.id

    @api.model
    def create(self, values):
        if values.get('employee_id'):
            employee = self.env['hr.employee'].browse(values['employee_id'])
            values.update({'department_id': employee.department_id.id})
        return super(OtherHrPayslip,self).create(values)

    def write(self, values):
        if values.get('employee_id'):
            employee = self.env['hr.employee'].browse(values['employee_id'])
            values.update({'department_id': employee.department_id.id})
        return super(OtherHrPayslip, self).write(values)

    def other_hr_payslip_done(self):
        for rec in self:
            rec.state = 'done'

    def set_draft(self):
        for rec in self:
            rec.state = 'draft'
