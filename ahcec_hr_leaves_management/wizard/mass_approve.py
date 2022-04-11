from odoo import models, api, _
from odoo.exceptions import UserError


class ApproveLeaveAllocation(models.TransientModel):
    _name = "approve.leave.allocation"
    _description = "Approve Leave Allocation"

    def approve_leave(self):
        context = dict(self._context or {})
        leaves = self.env['hr.holidays'].browse(context.get('active_ids'))
        leaves_to_post = self.env['hr.holidays']
        for leave in leaves:
            if leave.state == 'confirm':
                leaves_to_post += leave
        if not leaves_to_post:
            raise UserError(_('There is no leave allocation in To Approve state.'))
        leaves_to_post.action_approve()
        return {'type': 'ir.actions.act_window_close'}