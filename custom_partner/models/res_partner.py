# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):

    _inherit = 'res.partner'

    vat_dv = fields.Char( string="DV",
        help="Valor DV para formar el campo RUC")

