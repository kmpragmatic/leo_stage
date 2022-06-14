from odoo import fields, models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    mrp_cut_id = fields.Many2one('mrp.cut', 'Cutting Id')

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    mrp_cut_id = fields.Many2one('mrp.cut', 'Cutting Id', related='move_id.mrp_cut_id')
