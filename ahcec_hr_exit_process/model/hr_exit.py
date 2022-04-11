# -*- coding: utf-8 -*-

import time

# from openerp import models, fields, api, _
# from openerp.exceptions import Warning
from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.osv import expression
from datetime import datetime


class hr_exit(models.Model):
    _name = 'hr.exit'
    _description = "Exit"
    _rec_name = 'employee_id'
    # _inherit = ['mail.thread', 'ir.needaction_mixin']
    _inherit = ['mail.thread', 'mail.activity.mixin']  # odoo11
    _order = 'id desc'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    employee_id = fields.Many2one('hr.employee', required=True, string="Employee")
    request_date = fields.Datetime('Request Date', readonly='1',
                                   default=fields.Datetime.now())
    user_id = fields.Many2one('res.users', string='User',
                              default=lambda self: self.env.user,
                              states={'draft': [('readonly', False)]}, readonly=True)
    confirm_date = fields.Date(string='Submission Date',
                               readonly=True, copy=False)
    dept_approved_date = fields.Date(string='Completion Date',
                                     readonly=True, copy=False)
    validate_date = fields.Date(string='Approved Date(HR Manager)',
                                readonly=True, copy=False)
    general_validate_date = fields.Date(string='Approved Date(General Manager)',
                                        readonly=True, copy=False)

    confirm_by_id = fields.Many2one('res.users', string='Submitted By', readonly=True, copy=False)
    dept_manager_by_id = fields.Many2one('res.users', string='Completed By', readonly=True,
                                         copy=False)
    hr_manager_by_id = fields.Many2one('res.users', string='Approved By HR Manager', readonly=True, copy=False)
    gen_man_by_id = fields.Many2one('res.users', string='Approved By General Manager', readonly=True, copy=False)
    reason_for_leaving = fields.Char(string='Reason For Leaving', required=False, copy=False, readonly=True)

    reason_for_leaving_id = fields.Many2one('hr.exit.reason', string='Reason for Leaving')

    last_work_date = fields.Date(string='Last Day of Work')
    survey = fields.Many2one('survey.survey', string="Interview", readonly=True)
    # response_id = fields.Many2one('survey.user_input', "Response", ondelete="set null", oldname="response")
    response_id = fields.Many2one('survey.user_input', "Response", ondelete="set null")
    partner_id = fields.Many2one('res.partner', "Contact", readonly=True)
    # exit_checklist_ids = fields.One2many('hr.exit.checklist', 'exit_id')

    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('confirm', 'Submitted'),
        ('done', 'Completed'),
        ('cancel', 'Cancel'),
        ('reject', 'Rejected')], string='State',
        readonly=True, help='', default='draft',
        track_visibility='onchange')
    notes = fields.Text(string='Notes')
    manager_id = fields.Many2one('hr.employee', 'Head of Department',
                                 related='employee_id.department_id.manager_id',
                                 states={'draft': [('readonly', False)]}, readonly=True, store=True,
                                 help='This area is automatically filled by the user who \
                        will confirm the exit', copy=False)
    department_id = fields.Many2one(
        related='employee_id.department_id',
        string='OC', type='many2one', relation='hr.department',
        readonly=True, store=True)
    job_id = fields.Many2one(
        related='employee_id.job_id',
        string='Job Position', type='many2one', relation='hr.job',
        readonly=True, store=True)
    line_manager_id = fields.Many2one(
        related='employee_id.parent_id',
        string='Line Manager', type='many2one', relation='hr.employee',
        readonly=True, store=True)
    # job_title = fields.Many2one(
    #     related='employee_id.contract_id.job_id.job_title', readonly=True, store=True)
    # strata_id = fields.Char(
    #     related='employee_id.strata_id', readonly=True, store=True)
    # employment_status = fields.Selection(
    #     related='employee_id.contract_id.employment_status', readonly=True, store=True)
    checklist_ids = fields.One2many('hr.exit.line', 'exit_id', string="Checklist")
    contract_id = fields.Many2one('hr.contract', string='Contract', readonly=False)
    contract_ids = fields.Many2many('hr.contract', 'hr_contract_contract_tag')

    # reject_request = fields.Char('Reject Reason', readonly=1)

     #odoo13
    def action_makeMeeting(self):
        """ This opens Meeting's calendar view to schedule meeting on current applicant
            @return: Dictionary value for created Meeting view
        """
        #         self.ensure_one()
        #         partners = self.partner_id | self.user_id.partner_id | self.department_id.manager_id.user_id.partner_id

        #         category = self.env.ref('hr_recruitment.categ_meet_interview')
        res = self.env['ir.actions.act_window'].for_xml_id('calendar', 'action_calendar_event')
        #         res['context'] = {
        #             'search_default_partner_ids': self.partner_id.name,
        #             'default_partner_ids': partners.ids,
        #             'default_user_id': self.env.uid,
        #             'default_name': self.name,
        #             'default_categ_ids': category and [category.id] or False,
        #         }
        return res

    #odoo13
    def action_start_survey(self):
        self.ensure_one()
        # create a response and link it to this applicant
        if not self.response_id:
            response = self.env['survey.user_input'].create(
                {'survey_id': self.survey.id, 'partner_id': self.partner_id.id})
            self.response_id = response.id
        else:
            response = self.response_id
        # grab the token of the response and start surveying
        return self.survey.with_context(survey_token=response.token).action_start_survey()

    #odoo13
    def action_print_survey(self):
        """ If response is available then print this response otherwise print survey form (print template of the survey) """
        self.ensure_one()
        if not self.response_id:
            return self.survey.action_print_survey()
        else:
            response = self.response_id
            return self.survey.with_context(survey_token=response.token).action_print_survey()

    #odoo13
    def get_contract_latest(self, employee, date_from, date_to):
        """
        @param employee: browse record of employee
        @param date_from: date field
        @param date_to: date field
        @return: returns the ids of all the contracts for the given employee that need to be considered for the given dates
        """
        contract_obj = self.env['hr.contract']
        clause = []
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', employee.id), '|', '|'] + clause_1 + clause_2 + clause_3
        contract_ids = contract_obj.search(clause_final, limit=1)
        return contract_ids

    @api.onchange('employee_id', 'state')
    def get_contract(self):
        contract_obj = self.env['hr.contract']
        #        if not self.employee_id.address_home_id:
        #            raise Warning(_('The employee must have a home address.'))
        self.partner_id = self.employee_id.address_home_id.id
        all_contract_ids = contract_obj.search([('employee_id', '=', self.employee_id.id)])
        contract_ids = self.get_contract_latest(self.employee_id, self.request_date, self.request_date)
        if contract_ids:
            self.contract_id = contract_ids[0].id
            self.contract_ids = all_contract_ids.ids

        checklist_data = self.env['hr.exit.checklist'].search([])

        self.checklist_ids = False
        for checklist in checklist_data:
            if checklist.is_head_department:
                responsible_user = self.employee_id.department_id.manager_id.user_id
            elif checklist.is_line_manager:
                responsible_user = self.employee_id.parent_id.user_id
            else:
                responsible_user = checklist.responsible_user_id
            self.checklist_ids = [
                (0, 0, {'checklist_id': checklist.id, 'state': 'draft', 'notes': checklist.notes,
                        'responsible_user_id': responsible_user.id})]

        # for exit_checklist in self.checklist_ids:
        #     checkline = exit_checklist.checklist_id
        #     exit_checklist.checklist_unique_ids = [
        #         (0, 0, {'name': checkline.name, 'is_comments': checkline.is_comments})]

        return {'domain': {
            'contract_id': [('id', 'in', all_contract_ids.ids)]
        }}

    @api.onchange('request_date')
    def get_contract_1(self):
        contract_obj = self.env['hr.contract']
        all_contract_ids = contract_obj.search([('employee_id', '=', self.employee_id.id)])
        return {'domain': {
            'contract_id': [('id', 'in', all_contract_ids.ids)]
        }}

    #odoo13
    def exit_approved_by_department(self):
        obj_emp = self.env['hr.employee']
        self.state = 'confirm'
        self.dept_approved_date = time.strftime('%Y-%m-%d')

    #odoo13
    def request_set(self):
        self.state = 'draft'

    #odoo13
    def exit_cancel(self):
        self.state = 'cancel'

    #odoo13
    def get_confirm(self):
        self.state = 'confirm'
        self.confirm_date = time.strftime('%Y-%m-%d')
        self.confirm_by_id = self.env.user.id
        for checklist in self.checklist_ids:
            checklist.checklist_confirm()

    #odoo13
    def get_apprv_dept_manager(self):
        self.state = 'approved_dept_manager'
        self.dept_approved_date = time.strftime('%Y-%m-%d')
        self.dept_manager_by_id = self.env.user.id
        # checklist_data = self.env['hr.exit.checklist'].search([])
        # for checklist in checklist_data:
        #     vals = {'checklist_id': checklist.id,
        #             'exit_id': self.id,
        #             'state': 'confirm',
        #             'responsible_user_id': checklist.responsible_user_id.id,
        #             'checklist_line_ids': [(6, 0, checklist.checklist_line_ids.ids)]}
        #     self.env['hr.exit.line'].create(vals)

    #odoo13
    def get_apprv_hr_manager(self):
        self.state = 'approved_hr_manager'
        self.validate_date = time.strftime('%Y-%m-%d')
        self.hr_manager_by_id = self.env.user.id
        for record in self.checklist_ids:
            if not record.state in ['approved']:
                raise Warning(_(
                    'You can not approve this request since there are some checklist to be approved by respected department'))

    #odoo13
    def get_apprv_general_manager(self):
        self.state = 'approved_general_manager'
        self.general_validate_date = time.strftime('%Y-%m-%d')
        self.gen_man_by_id = self.env.user.id

    #odoo13
    def get_done(self):
        self.state = 'done'
        self.dept_approved_date = time.strftime('%Y-%m-%d')
        self.dept_manager_by_id = self.env.user.id
        for record in self.checklist_ids:
            if record.state != 'approved':
                raise Warning(_(
                    'You can not approve this request since there are some checklist yet to be completed'))

   #odoo13
    def get_reject(self):
        self.state = 'reject'

    @api.model
    def create(self, vals):
        previous_requests = self.env['hr.exit'].search([('employee_id', '=', vals.get('employee_id', ''))])
        if len(previous_requests) != 0:
            raise Warning(_(
                'You can not submit this request since there is a previous exit request related to this employee'))
        res = super(hr_exit, self).create(vals)
        checklists = res.checklist_ids
        for checklist in checklists:
            checklines = checklist.checklist_id.checklist_line_ids
            for checkline in checklines:
                checklist.checklist_unique_ids = [
                    (0, 0, {'name': checkline.name, 'is_comments': checkline.is_comments})]
        return res


class hr_exit_checklist_line(models.Model):
    _name = 'hr.exit.checklist.line'
    _description = 'HR Exit CheckList Line'

    name = fields.Char(string="Name", required=True)
    is_comments = fields.Boolean(string='Is Comments')
    checklist_line_id = fields.Many2one('hr.exit.checklist', invisible=True)


class ExitReason(models.Model):
    _name = 'hr.exit.reason'
    _description = 'HR Exit Reason'

    name = fields.Char(string="Name", required=True)
    description = fields.Char(string="Description")


class hr_exit_line(models.Model):
    _name = 'hr.exit.line'
    _description = "Exit Lines"
    # _inherit = ['mail.thread', 'ir.needaction_mixin']
    _inherit = ['mail.thread', 'mail.activity.mixin']  # odoo11
    _rec_name = 'checklist_id'
    _order = 'id desc'

    checklist_id = fields.Many2one('hr.exit.checklist', string="Checklist", required=True, ondelete="cascade")
    notes = fields.Text(string="Remarks")
    state = fields.Selection(selection=[('draft', 'New'),
                                        ('confirm', 'Submitted'),
                                        ('approved', 'Completed'),
                                        ('reject', 'Rejected'),
                                        ('cancel', 'Cancelled')],
                             string='State', default='draft', track_visibility='onchange')
    exit_id = fields.Many2one('hr.exit')
    responsible_user_id = fields.Many2one('res.users', string='Responsible User', required=True)
    user_id = fields.Many2one(related="exit_id.user_id", string="User", type='many2one', relation='res.users',
                              readonly=True, store=True)
    checklist_line_ids = fields.Many2many('hr.exit.checklist.line',
                                          'rel_exit_checklist_line', 'exit_line_id', 'checklist_exit_line_id',
                                          string='Checklist Lines')
    checklist_unique_ids = fields.One2many('hr.exit.checklist.unique.line', 'checklist_line_id')

    related_employee_id = fields.Many2one(related='exit_id.employee_id')
    request_date = fields.Datetime(related='exit_id.request_date')
    last_work_date = fields.Date(related='exit_id.last_work_date')
    line_manager_id = fields.Many2one(related='exit_id.line_manager_id')
    # job_title = fields.Many2one(related='exit_id.job_title')
    # employment_status = fields.Selection(related='exit_id.employment_status')
    department_id = fields.Many2one(related='exit_id.department_id')
    job_id = fields.Many2one(related='exit_id.job_id')
    # user_id = fields.Many2one(related='exit_id.user_id')
    manager_id = fields.Many2one(related='exit_id.manager_id')
    confirm_date = fields.Date(related='exit_id.confirm_date')
    confirm_by_id = fields.Many2one(related='exit_id.confirm_by_id')
    dept_approved_date = fields.Date(related='exit_id.dept_approved_date')
    validate_date = fields.Date(related='exit_id.validate_date')
    general_validate_date = fields.Date(related='exit_id.general_validate_date')
    dept_manager_by_id = fields.Many2one(related='exit_id.dept_manager_by_id')
    hr_manager_by_id = fields.Many2one(related='exit_id.hr_manager_by_id')
    gen_man_by_id = fields.Many2one(related='exit_id.gen_man_by_id')
    survey = fields.Many2one(related='exit_id.survey')
    partner_id = fields.Many2one(related='exit_id.partner_id')
    reason_for_leaving_id = fields.Many2one(related='exit_id.reason_for_leaving_id')
    related_notes = fields.Text(related='exit_id.notes')
    completion_date = fields.Datetime(string="Checklist Completion Date")
    # strata_id = fields.Char(related='exit_id.strata_id')

    request_state = fields.Selection(related='exit_id.state', string='Request Status')
    reject_request = fields.Char(string='Reject Reason', readonly=1)

    # checklist_unique_ids = fields.One2many('hr.exit_id.checklist.unique.line', 'checklist_id')

    @api.onchange('checklist_id')
    def get_checklistline(self):
        self.checklist_line_ids = self.checklist_id.checklist_line_ids

        # Responsible user added
        self.responsible_user_id = self.checklist_id.responsible_user_id

    #odoo13
    def checklist_confirm(self):
        self.state = 'confirm'

    #odoo13
    def checklist_approved(self):
        for line in self.checklist_unique_ids:
            if not line.is_comments and not line.completed:
                raise Warning(_(
                    'You can not approve this checklist since there are some line not completed yet'))
        self.state = 'approved'
        self.completion_date = datetime.now()

    #odoo13
    def checklist_cancel(self):
        self.state = 'cancel'

    #odoo13
    def checklist_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Reason',
            'res_model': 'hr.exit.reject.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': self.env.ref('ahcec_hr_exit_process.hr_exit_reject_reason_wizard_view_form').id,
            'context': {
                'related_name': self._name,
                'active_id': self.id
            }
        }

    #odoo13
    def request_set(self):
        self.state = 'draft'

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if self.env.user.has_group('hr.group_hr_user'):
            domain = expression.AND([domain, [('responsible_user_id', '=', self.env.user.id)]])
            return super(hr_exit_line, self.sudo()).search_read(domain=domain, fields=fields, offset=offset,
                                                                limit=limit, order=order)
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)


class hr_exit_checklist(models.Model):
    _name = 'hr.exit.checklist'
    _description = 'HR Exit CheckList'

    name = fields.Char(string="Name", required=True)
    is_head_department = fields.Boolean(string='Is Head Department', required=False, default=False)
    is_line_manager = fields.Boolean(string='Is Line Manager', required=False, default=False)
    responsible_user_id = fields.Many2one('res.users', string='Responsible User', required=False)
    notes = fields.Text(string="Notes")
    checklist_line_ids = fields.One2many('hr.exit.checklist.line', 'checklist_line_id', string='Checklist')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
