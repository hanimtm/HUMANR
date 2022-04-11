# -*- coding: utf-8 -*-

from odoo import models, fields


class hr_exit_checklist_unique_line(models.Model):
    _name = 'hr.exit.checklist.unique.line'
    _description = 'HR Exit CheckList Unique Line'

    name = fields.Char(string="Name", required=True)
    # checklist_id = fields.Many2one('hr.exit.checklist', string='Exit CheckList')
    checklist_line_id = fields.Many2one('hr.exit.line', string='CheckList')
    completed = fields.Boolean(string="Complete")
    is_comments = fields.Boolean(string='Is Comments')
    comments = fields.Char(string='Comments')

    def mark_completed(self):
        self.completed = True

    def mark_not_completed(self):
        self.completed = False
