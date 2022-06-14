from odoo import fields, models, api


class StockLocation(models.Model):
    _inherit = "stock.location"

    usage = fields.Selection(selection_add=[('cutting', 'Cutting')], ondelete={'cutting': 'cascade'})

