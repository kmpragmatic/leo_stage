{
    'name': "Cutting Process",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Pragmatic S.A.C.",
    'website': "https://www.pragmatic.com.pe",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Manufacturing/Manufacturing',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mrp'],

    # always loaded
    'data': [
        'security/cutting.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/product_template.xml',
        'views/stock_move.xml',
        'views/mrp_bom.xml',
        'views/mrp_cut_view.xml',

    ],

}
# -*- coding: utf-8 -*-
