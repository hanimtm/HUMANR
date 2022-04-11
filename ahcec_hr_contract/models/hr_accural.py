# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ticket_accural_debit_account = fields.Many2one('account.account', 'Ticket Accrual Debit Account')
    ticket_accural_credit_account = fields.Many2one('account.account', 'Ticket Accrual Credit Account')
    ticket_accural_debit_pjt_account = fields.Many2one('account.account', 'Ticket Accrual Debit Account(Project)')
    ticket_accural_credit_pjt_account = fields.Many2one('account.account', 'Ticket Accrual Credit Account(Project)')

    eos_accural_debit_account = fields.Many2one('account.account', 'EOS Accrual Debit Account')
    eos_accural_credit_account = fields.Many2one('account.account', 'EOS Accrual Credit Account')
    eos_accural_debit_pjt_account = fields.Many2one('account.account', 'EOS Accrual Debit Account(Project)')
    eos_accural_credit_pjt_account = fields.Many2one('account.account', 'EOS Accrual Credit Account(Project)')

    vacation_accural_debit_account = fields.Many2one('account.account', 'Vacation Accrual Debit Account')
    vacation_accural_credit_account = fields.Many2one('account.account', 'Vacation Accrual Credit Account')
    vacation_accural_debit_pjt_account = fields.Many2one('account.account', 'Vacation Accrual Debit Account(Project)')
    vacation_accural_credit_pjt_account = fields.Many2one('account.account', 'Vacation Accrual Credit Account(Project)')

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('ticket_debit_account', self.ticket_accural_debit_account.id)
        self.env['ir.config_parameter'].sudo().set_param('ticket_credit_account', self.ticket_accural_credit_account.id)
        self.env['ir.config_parameter'].sudo().set_param('ticket_debit_pjt_account',
                                                         self.ticket_accural_debit_pjt_account.id)
        self.env['ir.config_parameter'].sudo().set_param('ticket_credit_pjt_account',
                                                         self.ticket_accural_credit_pjt_account.id)
        self.env['ir.config_parameter'].sudo().set_param('eos_debit_account', self.eos_accural_debit_account.id)
        self.env['ir.config_parameter'].sudo().set_param('eos_credit_account', self.eos_accural_credit_account.id)
        self.env['ir.config_parameter'].sudo().set_param('eos_debit_pjt_account', self.eos_accural_debit_pjt_account.id)
        self.env['ir.config_parameter'].sudo().set_param('eos_credit_pjt_account',
                                                         self.eos_accural_credit_pjt_account.id)
        self.env['ir.config_parameter'].sudo().set_param('vacation_debit_account',
                                                         self.vacation_accural_debit_account.id)
        self.env['ir.config_parameter'].sudo().set_param('vacation_credit_account',
                                                         self.vacation_accural_credit_account.id)
        self.env['ir.config_parameter'].sudo().set_param('vacation_debit_pjt_account',
                                                         self.vacation_accural_debit_pjt_account.id)
        self.env['ir.config_parameter'].sudo().set_param('vacation_credit_pjt_account',
                                                         self.vacation_accural_credit_pjt_account.id)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            ticket_accural_debit_account=int(self.env['ir.config_parameter'].sudo().get_param('ticket_debit_account')),
            ticket_accural_credit_account=int(
                self.env['ir.config_parameter'].sudo().get_param('ticket_credit_account')),
            ticket_accural_debit_pjt_account=int(
                self.env['ir.config_parameter'].sudo().get_param('ticket_debit_pjt_account')),
            ticket_accural_credit_pjt_account=int(
                self.env['ir.config_parameter'].sudo().get_param('ticket_credit_pjt_account')),
            eos_accural_debit_account=int(self.env['ir.config_parameter'].sudo().get_param('eos_debit_account')),
            eos_accural_credit_account=int(self.env['ir.config_parameter'].sudo().get_param('eos_credit_account')),
            eos_accural_debit_pjt_account=int(
                self.env['ir.config_parameter'].sudo().get_param('eos_debit_pjt_account')),
            eos_accural_credit_pjt_account=int(
                self.env['ir.config_parameter'].sudo().get_param('eos_credit_pjt_account')),
            vacation_accural_debit_account=int(
                self.env['ir.config_parameter'].sudo().get_param('vacation_debit_account')),
            vacation_accural_credit_account=int(
                self.env['ir.config_parameter'].sudo().get_param('vacation_credit_account')),
            vacation_accural_debit_pjt_account=int(
                self.env['ir.config_parameter'].sudo().get_param('vacation_debit_pjt_account')),
            vacation_accural_credit_pjt_account=int(
                self.env['ir.config_parameter'].sudo().get_param('vacation_credit_pjt_account')),
        )
        return res


class EmployeeAccrualMove(models.Model):
    _name = 'employee.accrual.move'

    move_id = fields.Many2one('account.move', 'Journal Entry', readonly=True)
    employee_id = fields.Many2one('hr.employee', 'Employee', readonly=True)
    date_from = fields.Date('From', readonly=True)
    date_to = fields.Date('To', readonly=True)
    type = fields.Selection([('eos', 'EOS'),
                             ('ticket', 'Ticket'),
                             ('vacation', 'Vacation'),
                             ('reverse', 'Reverse')
                             ], string='Type', readonly=True)
    state = fields.Selection(string='Status', related='move_id.state')
