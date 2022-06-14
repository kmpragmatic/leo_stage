from odoo import fields, models, api


class PickingType(models.Model):
    _inherit = 'stock.picking.type'

    code = fields.Selection(selection_add=[('mrp_cutting', 'Cutting')], ondelete={'mrp_cutting': 'cascade'})
