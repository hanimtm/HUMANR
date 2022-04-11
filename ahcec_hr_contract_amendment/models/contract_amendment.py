# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from datetime import datetime
import time
from odoo import SUPERUSER_ID

# html_data = """
#     <html>
#     <head>
#     <meta http-equiv="Content-type" content="text/html; charset=utf-8" />
#     </head>
#     <body>
#     <table border="0" cellspacing="10" cellpadding="0" width="100%%"
#     style="font-family: Arial, Sans-serif; font-size: 14">
#     <tr>
#         <td width="100%%">Hello
#         AMENDMENT TO CONTRACT Employment Agreement
#         Between your company
#         and %s dated %s
#         <br/>
#         The following amendments/add to above referenced contract will be made effective from %s
#         Paragraph %s in the above reference contract your compnay and %s
#         acknowledge that as of %s the employee will amendment from %s %s to %s %s
#         the employees %s, %s and %s will be replaced with %s - %s %s,%s
#         Paragraph Other your current base location %s will change to %s.
#     </td>
#     </tr>
#     </table>
#     </body>
#     </html>"""


class ContractAmendment(models.Model):
    _name = 'contract.amendment'
    _inherit = 'mail.thread'
    _description = "Contract Amendment"
    _inherit = ['mail.thread']

    employee_id = fields.Many2one('hr.employee', 'Employee', required=True, default=lambda self: self.env['hr.employee'].get_employee())
    hr_contract_id = fields.Many2one('hr.contract', 'Contract', required=True, domain=[('employee_id', '=', 'employee_id.id')])
    job_id = fields.Many2one('hr.job', 'From Job', readonly=True)
    department_id = fields.Many2one('hr.department', 'From Department', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, default=lambda self: self.env.user.company_id)
    effective_date = fields.Date('Effective Date', default=time.strftime('%Y-%m-%d'),track_visibility='onchange')
    new_department_id = fields.Many2one('hr.department', 'To Department',track_visibility='onchange')
    new_job_id = fields.Many2one('hr.job', 'To Job',track_visibility='onchange')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'), ('validate', 'Validate'), ('approve', 'Approved'), ('done', 'Done'), ('cancel', 'Cancel')], 'State', default='draft', track_visibility='onchange')
    description = fields.Text('Description')
    current_start_date = fields.Date('Current Contract From')
    current_end_date = fields.Date('Current Contract To')
    new_start_date = fields.Date('New Contract From',track_visibility='onchange')
    new_end_date = fields.Date('New Contract To',track_visibility='onchange')
    approved_date = fields.Datetime('Approved Date', readonly=True, copy=False)
    approved_by = fields.Many2one('res.users', 'Approved by', readonly=True, copy=False)
    validated_by = fields.Many2one('res.users', 'Validated by', readonly=True, copy=False)
    validated_date = fields.Datetime('Validated Date', readonly=True, copy=False)
    package_id = fields.One2many('contract.package.line','amendment_id','Packages',track_visibility='onchange')


    @api.onchange('employee_id')
    def onchange_employee_id(self):
        effective_date = time.strftime('%Y-%m-%d')
        payslip_obj = self.env['hr.payslip']
        contract_ids = payslip_obj.get_contract(self.employee_id, effective_date, effective_date)
        contract = payslip_obj.browse(contract_ids)
        self.department_id = self.employee_id.department_id.id or False
        self.job_id = self.employee_id.job_id.id or False
        self.hr_contract_id = contract and contract[0].id or False

    @api.onchange('hr_contract_id')
    def onchange_hr_contract_id(self):
        self.current_start_date = self.hr_contract_id.date_start
        self.current_end_date = self.hr_contract_id.date_end

    @api.model
    def create(self, vals):
        if vals.get('employee_id', False):
            employee = self.env['hr.employee'].browse(vals['employee_id'])
            vals.update({'department_id': employee.department_id.id or False,
                         'job_id': employee.job_id.id or False,
            })
        return super(ContractAmendment, self).create(vals)

    def write(self, vals):
        if vals.get('employee_id', False):
            employee = self.env['hr.employee'].browse(vals.get('employee_id'))
            vals.update({'department_id': employee.department_id.id or False,
                        'job_id': employee.job_id.id or False,
            })
        return super(ContractAmendment, self).write(vals)

    @api.depends('employee_id')
    def name_get(self):
        result = []
        for amendment in self:
            name = amendment.employee_id.name or ''
            result.append((amendment.id, name))
        return result

    def unlink(self):
        for objects in self:
            if objects.state in ['confirm', 'validate', 'approve', 'done', 'cancel']:
                raise UserError(_('You cannot remove the record which is in %s state!') % (objects.state))
        return super(ContractAmendment, self).unlink()

    def amendment_confirm(self):
        self.ensure_one()
        # warnings = self.env['issue.warning'].search([('id', 'in', self.employee_id.issue_warning_ids.ids), ('warning_action', '=', 'prohibit'), ('state', '=', 'done')])
        # for warning in warnings:
        #     if self.effective_date >= warning.start_date and self.effective_date <= warning.end_date:
        #         raise UserError(_("You can't Confirm Contract Amendment because %s have Prohibit Benefit Upgrades Warning.") % self.employee_id.name)
        self.write({'state': 'confirm'})

    def amendment_validate(self):
        self.ensure_one()
        # hop_groups_config_obj = self.env['hr.groups.configuration']
        # hop_groups_config_ids = hop_groups_config_obj.search([('branch_id', '=', self.employee_id.branch_id.id or False), ('hop_ids', '!=', False)])
        # user_ids = hop_groups_config_ids and [employee.user_id.id for employee in hop_groups_config_ids.hop_ids if employee.user_id] or []
        # self.message_subscribe_users(user_ids)
        today = datetime.today()
        user = self.env.user
        self.write({'state': 'validate', 'validated_by': user.id, 'validated_date': today})

    def amendment_approve(self):
        self.ensure_one()
        today = datetime.today()
        user = self.env.user
        self.write({'state': 'approve', 'approved_by': user.id, 'approved_date': today})

    def amendment_done(self):
        self.ensure_one()
        # value = self.env['hr.employee'].browse(self.employee_id.id)
        # self.employee_id.department_id = self.new_department_id.id or False
        # self.employee_id.job_id = self.new_job_id.id or False
        #
        # self.hr_contract_id.date_start = self.current_start_date or False
        # self.hr_contract_id.date_end = self.current_end_date or False
        #
        # for package in self.package_id:
        #     if package.name == 'basic':
        #         self.hr_contract_id.wage = package.new_package
        #         package.approved_date = fields.Date.today()
        #     elif package.name == 'transport':
        #         self.hr_contract_id.is_TA = True
        #         self.hr_contract_id.TA = package.new_package
        #         package.approved_date = fields.Date.today()
        #     elif package.name == 'hra':
        #         self.hr_contract_id.is_HRA = True
        #         self.hr_contract_id.HRA = package.new_package
        #         package.approved_date = fields.Date.today()
        #     elif package.name == 'mobile':
        #         self.hr_contract_id.mobile = True
        #         self.hr_contract_id.mobile_allowance = package.new_package
        #     elif package.name == 'mobile':
        #         self.hr_contract_id.mobile = True
        #         self.hr_contract_id.mobile_allowance = package.new_package
        #         package.approved_date = fields.Date.today()
        #     elif package.name == 'shift':
        #         self.hr_contract_id.is_shift_allow = True
        #         self.hr_contract_id.shift_allow = package.new_package
        #         package.approved_date = fields.Date.today()
        #     elif package.name == 'remote':
        #         self.hr_contract_id.is_remote_allow = True
        #         self.hr_contract_id.remote_allow = package.new_package
        #         package.approved_date = fields.Date.today()
        #     elif package.name == 'other':
        #         self.hr_contract_id.is_other_allow = True
        #         self.hr_contract_id.other_allow = package.new_package
        #         package.approved_date = fields.Date.today()

        self.write({'state': 'done'})

    def amendment_cancel(self):
        self.ensure_one()
        self.write({'state': 'cancel'})

    def set_to_draft_user(self):
        self.set_to_draft()

    def set_to_draft(self):
        self.ensure_one()
        # value = self.env['hr.employee'].browse(self.employee_id.id)
        self.employee_id.department_id = self.department_id.id or False
        # for package in self.package_id:
        #     if package.name == 'basic':
        #         self.hr_contract_id.wage = package.current_package
        #     elif package.name == 'transport':
        #         self.hr_contract_id.is_TA = True
        #         self.hr_contract_id.TA = package.current_package
        #     elif package.name == 'hra':
        #         self.hr_contract_id.is_HRA = True
        #         self.hr_contract_id.HRA = package.current_package
        #     elif package.name == 'mobile':
        #         self.hr_contract_id.mobile = True
        #         self.hr_contract_id.mobile_allowance = package.current_package
        #     elif package.name == 'mobile':
        #         self.hr_contract_id.mobile = True
        #         self.hr_contract_id.mobile_allowance = package.current_package
        #     elif package.name == 'shift':
        #         self.hr_contract_id.is_shift_allow = True
        #         self.hr_contract_id.shift_allow = package.current_package
        #     elif package.name == 'remote':
        #         self.hr_contract_id.is_remote_allow = True
        #         self.hr_contract_id.remote_allow = package.current_package
        #     elif package.name == 'other':
        #         self.hr_contract_id.is_other_allow = True
        #         self.hr_contract_id.other_allow = package.current_package
        self.write({'state': 'draft'})

class PackageLine(models.Model):
    _name = 'contract.package.line'

    amendment_id = fields.Many2one('contract.amendment', 'Amendment',required=True)
    name = fields.Selection([('basic', 'Basic'), ('hra', 'Housing Allowance'), ('transport', 'Transportation Allowance'),
        ('csd', 'C & SD Allowance'), ('mobile', 'Mobile Allowance'), ('shift', 'Shift Allowance'), ('remote', 'Remote Area Allowance'),
        ('Other', 'Other Allowance')],'Type', required=True)
    current_package = fields.Float('Current Package')
    change_value = fields.Float('Increment/Decrement Value',required=True)
    new_package = fields.Float('New Package',compute='_compute_new_package', required=True)
    state = fields.Selection(related='amendment_id.state',store=True)
    employee_id = fields.Many2one('hr.employee',related='amendment_id.employee_id',store=True)
    hr_contract_id = fields.Many2one('hr.contract',related='amendment_id.hr_contract_id',store=True)
    approved_date = fields.Date('Amendment Approved on')
    effective_date = fields.Date(related='amendment_id.effective_date',store=True)

    @api.depends('name','change_value','current_package')
    def _compute_new_package(self):
        self.new_package = self.current_package + self.change_value

    @api.onchange('name','amendment_id')
    def onchange_name(self):
        for package in self:
            contract = package.amendment_id.hr_contract_id
            if contract:
                if package.name == 'basic':
                    package.current_package = contract.wage
                elif package.name == 'transport':
                    package.current_package = contract.TA
                elif package.name == 'hra':
                    package.current_package = contract.HRA
                elif package.name == 'csd':
                    package.current_package = contract.cda
                elif package.name == 'mobile':
                    package.current_package = contract.mobile_allowance
                elif package.name == 'shift':
                    package.current_package = contract.shift_allow
                elif package.name == 'remote':
                    package.current_package = contract.remote_allow
                elif package.name == 'other':
                    package.current_package = contract.other_allow

class HrContract(models.Model):
    _inherit = 'hr.contract'

    amendment_ids = fields.One2many('contract.package.line', 'hr_contract_id', string='Contracts Amendments')
    amendment_count = fields.Integer(compute='_compute_amendment_count', string='Amendment Count')

    def _compute_amendment_count(self):
        amd = self.env['contract.amendment']
        for amendment in self:
            amendments = amd.search([('hr_contract_id', '=', amendment.id),('state','=','done')])
            amendment.amendment_ids = amendments.ids
            amendment.amendment_count = len(amendments.ids)

