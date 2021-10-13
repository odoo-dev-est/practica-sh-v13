# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api
from .utils import *
from odoo.tools.translate import _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
import logging
import json
_logger = logging.getLogger(__name__)
try:
    from lxml import etree
except:
    _logger.warning("no se ha cargado lxml !!!")


class ResPartner(models.Model):

    _inherit = 'res.partner'

    __check_vat_pa_re1 = re.compile(r'(PE|E)-\d{1,3}-\d{1,5}$')
    __check_vat_pa_re2 = re.\
        compile(r'((\d|1[0-2]|N)|(\d|1[0-2])-(PI|AV|NT|N))-\d{1,3}-\d{1,5}$')
    __check_vat_pa_re3 = re.compile(r'\d{1,7}-\d{1,4}-\d{1,6}$')
    __check_vat_pa_re4 = re.compile(r'PAS\d{1,27}$')
    __check_vat_pa_re5 = re.compile(r'(\d|1[0-2])-NT-\d{1,3}-\d{1,5}$')
    _regex_country_vat_dv = r"(?P<country>[A-Z]{2})(((?P<vatwdv>.*)"\
                            r"DV(?P<dv>.*))|(?P<vat>.*))"
    _check_country_vat_dv_re = re.compile(_regex_country_vat_dv)

    vat_country_id = fields.Many2one(
        'res.country', string="País",
        ondelete="set null",
        compute='_get_vat_country_id',
        inverse='_get_new_vat',
        help="País para formar el campo TIN")

    vat_alone = fields.Char(
        string="RUC", size=25,
        compute='_get_vat_alone',
        inverse='_get_new_vat',
        help="Valor del RUC para formar el campo TIN")

    vat_dv = fields.Char(
        string="DV", size=2,
        compute='_get_vat_dv',
        inverse='_get_new_vat',
        help="Valor DV para formar el campo RUC")


    def update_json_data(self, json_data=False, update_data={}):
        ''' It updates JSON data. It gets JSON data, converts it to a Python
        dictionary, updates this, and converts the dictionary to JSON data
        again. '''
        dict_data = json.loads(json_data) if json_data else {}
        dict_data.update(update_data)
        return json.dumps(dict_data, ensure_ascii=False)

    def set_modifiers(self, element=False, modifiers_upd={}):
        ''' It updates the JSON modifiers with the specified data to indicate
        if a XML tag is readonly or invisible or not. '''
        if element is not False:  # Do not write only if element:
            modifiers = element.get('modifiers') or {}
            modifiers_json = self.update_json_data(
                modifiers, modifiers_upd)
            element.set('modifiers', modifiers_json)

    """
        This method will show, it will allow to show only these fields when it is the Panamanian location.
    """ 
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(ResPartner, self).fields_view_get(view_id=view_id,view_type=view_type,toolbar=toolbar,submenu=submenu)
        if view_type in ['form','kanban']:
            company_obj  = self.env['res.company'].browse(self.env.context['allowed_company_ids'])
            document = etree.XML(res['arch'])
            if company_obj.country_id.code != 'PA': 
                fields =[
                        document.xpath("//field[@name='vat_alone']"),
                        document.xpath("//field[@name='vat_dv']"),
                    ]
                for field in fields:
                    if field:
                        self.set_modifiers(field[0], {'invisible': True, })
                
            elif company_obj.country_id.code == 'PA':
                vat  =  document.xpath("//field[@name='vat']")
                if vat:
                    vat[0].set('placeholder','Por Ejemplo ,PA0-000-000DV00')

            res['arch'] = etree.tostring(document,encoding='unicode')
        return res

    
    """
        This method will show, it will allow to show only these fields when it is the Panamanian location.
    """
    
    def check_vat_pa(self, vat):
        vat_split_dv = vat.split('DV')
        vat = vat_split_dv[0]
        calculateDV(vat)
        if self.__check_vat_pa_re1.match(vat) or self.__check_vat_pa_re2.\
                match(vat) or self.__check_vat_pa_re3.match(vat) or self.\
                __check_vat_pa_re4.match(vat) or self.__check_vat_pa_re5.\
                match(vat):
            if len(vat_split_dv) == 2:
                return calculateDV(vat) == vat_split_dv[-1]
            return True
        return False
    #Qa Ready
    @api.depends('vat')
    def _get_vat_country_id(self):
        """ Get the country object from the VAT field """
        for partner in self:
            partner.vat_country_id = None
            match_country_vat_dv = partner._check_country_vat_dv_re.match(partner.vat or '')
            if match_country_vat_dv:
                country_code = match_country_vat_dv.group('country')
                country_ids = self.env['res.country'].search([('code', '=', country_code)], limit=1)
                if country_ids:
                    partner.vat_country_id = country_ids.id
                    partner.country_id = country_ids.id
            elif not partner.id:
                # This section process "default" case.
                company_pool = self.env['res.company']
                company_default_id = self.env.user.company_id
                partner.vat_country_id = company_pool.browse(
                    company_default_id.id).country_id.id
                partner.country_id = company_pool.browse(
                    company_default_id.id).country_id.id

    @api.depends('vat')
    def _get_vat_alone(self):
        """ Get the RUC value from the VAT field """
        for partner in self:
            partner.vat_alone = ""
            match_country_vat_dv = partner._check_country_vat_dv_re.match(partner.vat or '')

            if match_country_vat_dv:
                partner.vat_alone = match_country_vat_dv.group('vatwdv') \
                    or match_country_vat_dv.group('vat')

    @api.depends('vat')
    def _get_vat_dv(self):
        """ Get the DV value from the VAT field """
        for partner in self:
            partner.vat_dv = ""
            match_country_vat_dv = partner.commercial_partner_id._check_country_vat_dv_re.match(partner.vat or '')
            if match_country_vat_dv:
                partner.vat_dv = match_country_vat_dv.group('dv')
        
    @api.depends('vat_country_id', 'vat_alone', 'vat_dv')
    def _get_new_vat(self):
        """ Get the value for VAT field through the 3 component fields """
        for partner in self:
            new_vat = partner.vat_country_id.code or ''
            new_vat += partner.vat_alone or ''
            if partner.vat_dv:
                new_vat += "DV{}".format(partner.vat_dv)
            partner.vat = new_vat
 
    @api.constrains('vat', 'country_id')
    def check_vat(self):
        for obj in self:
            if self.env.context['tz'] == 'America/Panama':
                if not obj.vat or obj.parent_id:
                    continue
                partner = self.env['res.partner'].search(
                    [
                        ('vat', '=', obj.vat),
                        ('id', '!=', obj.id),
                    ])
                if  partner:
                    raise UserError(_('El rut: %s debe ser único') % obj.vat) 
                self.check_vat_pa(obj.vat)  
                return True                    
        return super(ResPartner,self).check_vat()
