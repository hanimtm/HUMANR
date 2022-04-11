from odoo import fields, models, api


class HrExitRejectRequestWizard(models.TransientModel):
    _name = 'hr.exit.reject.reason.wizard'
    _description = 'Reject Request'

    reject_reason = fields.Char('Reason', required=True)

    def processed_and_send_email(self):
        active_id = self._context.get('active_id')
        request_id = self.env['hr.exit.line'].search([('id', '=', active_id)])
        request_id.activity_schedule('ahcec_hr_exit_process.mail_activity_reject_request_employee',
                                     user_id=request_id.confirm_by_id.id,
                                     note=self.reject_reason)
        request_id.reject_request = self.reject_reason
        request_id.state = 'reject'


        # reject_template_id = self.env.ref('hr_exit_process.hr_exit_reject_reason_email_template').id
        # template = self.env['mail.template'].browse(reject_template_id)
        # template.send_mail(self.id, force_send=True)
