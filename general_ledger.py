# This file is part of account_jasper_reports for tryton.  The COPYRIGHT file
# at the top level of this repository contains the full copyright notices and
# license terms.
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.pyson import Eval
from trytond.modules.jasper_reports.jasper import JasperReport

__all__ = ['PrintGeneralLedgerStart', 'PrintGeneralLedgerCompany',
    'PrintGeneralLedger', 'GeneralLedgerReport']


class PrintGeneralLedgerStart(ModelView):
    'Print General Ledger'
    __name__ = 'account_jasper_reports_multicompany.print_general_ledger.start'
    companies = fields.One2Many(
        'account_jasper_reports_multicompany.print_general_ledger.company',
        'start', 'Companies', required=True)
    account_templates = fields.Many2Many('account.account.template', None,
        None, 'Accounts')
    parties = fields.Many2Many('party.party', None, None, 'Parties')
    output_format = fields.Selection([
            ('pdf', 'PDF'),
            ('xls', 'XLS'),
            ], 'Output Format', required=True)

    @staticmethod
    def default_output_format():
        return 'pdf'


class PrintGeneralLedgerCompany(ModelView):
    'Print General Ledger - Company'
    __name__ = (
        'account_jasper_reports_multicompany.print_general_ledger.company')
    start = fields.Many2One(
        'account_jasper_reports_multicompany.print_general_ledger.start',
        'Start', required=True)
    company = fields.Many2One('company.company', 'Company', required=True)
    fiscalyear = fields.Many2One('account.fiscalyear', 'Fiscal Year',
        required=True,
        domain=[
            ('company', '=', Eval('company')),
            ], depends=['company'])
    start_period = fields.Many2One('account.period', 'Start Period',
        required=True,
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '<=', (Eval('end_period'), 'start_date')),
            ], depends=['fiscalyear', 'end_period'])
    end_period = fields.Many2One('account.period', 'End Period',
        required=True,
        domain=[
            ('fiscalyear', '=', Eval('fiscalyear')),
            ('start_date', '>=', (Eval('start_period'), 'start_date'))
            ],
        depends=['fiscalyear', 'start_period'])

    @fields.depends('company')
    def on_change_company(self):
        FiscalYear = Pool().get('account.fiscalyear')
        return {
            'fiscalyear': (FiscalYear.find(self.company.id, exception=False)
                if self.company else None),
            'start_period': None,
            'end_period': None,
            }

    @fields.depends('fiscalyear')
    def on_change_fiscalyear(self):
        return {
            'start_period': None,
            'end_period': None,
            }


class PrintGeneralLedger(Wizard):
    'Print GeneralLedger'
    __name__ = 'account_jasper_reports_multicompany.print_general_ledger'
    start = StateView(
        'account_jasper_reports_multicompany.print_general_ledger.start',
        ('account_jasper_reports_multicompany'
            '.print_general_ledger_start_view_form'), [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateAction(
        'account_jasper_reports_multicompany.report_general_ledger')

    def do_print_(self, action):
        data = {
            'companies': [],
            'account_templates': [x.id for x in self.start.account_templates],
            'parties': [x.id for x in self.start.parties],
            'output_format': self.start.output_format,
            }
        for company in self.start.companies:
            data['companies'].append({
                'company': company.company.id,
                'fiscalyear': company.fiscalyear.id,
                'start_period': (company.start_period.id
                    if company.start_period else None),
                'end_period': (company.end_period.id
                    if company.end_period else None),
                })
        return action, data

    def transition_print_(self):
        return 'end'

    def default_start(self, fields):
        pool = Pool()
        FiscalYear = pool.get('account.fiscalyear')
        Party = pool.get('party.party')

        account_ids = []
        party_ids = []
        if Transaction().context.get('model') == 'party.party':
            for party in Party.browse(Transaction().context.get('active_ids')):
                if party.account_payable and party.account_payable.template:
                    account_ids.append(party.account_payable.template.id)
                if (party.account_receivable
                        and party.account_receivable.template):
                    account_ids.append(party.account_receivable.template.id)
                party_ids.append(party.id)
        return {
            'companies': [{
                    'company': Transaction().context.get('company'),
                    'fiscalyear': FiscalYear.find(
                        Transaction().context.get('company'), exception=False),
                    }],
            'account_templates': account_ids,
            'parties': party_ids,
            }


class GeneralLedgerReport(JasperReport):
    __name__ = 'account_jasper_reports_multicompany.general_ledger'

    @classmethod
    def prepare(cls, data):
        pool = Pool()
        AccountTemplate = pool.get('account.account.template')
        Company = pool.get('company.company')
        FiscalYear = pool.get('account.fiscalyear')
        Line = pool.get('account.move.line')
        Party = pool.get('party.party')
        Period = pool.get('account.period')

        companies = []
        filter_companies = []
        filter_periods = []
        for company_data in data['companies']:
            company = Company(company_data['company'])
            fiscalyear = FiscalYear(company_data['fiscalyear'])
            start_period = Period(company_data['start_period'])
            end_period = Period(company_data['end_period'])
            companies.append({
                    'company': company,
                    'fiscalyear': fiscalyear,
                    'start_period': start_period,
                    'end_period': end_period,
                    })
            filter_companies.append(company)
            filter_periods += fiscalyear.get_periods(start_period, end_period)

        with Transaction().set_context(active_test=False):
            account_templates = AccountTemplate.browse(
                data.get('account_templates', []))
            parties = Party.browse(data.get('parties', []))
            if account_templates:
                accounts_subtitle = []
                for template in account_templates:
                    if len(accounts_subtitle) > 4:
                        accounts_subtitle.append('...')
                        break
                    if template.code:
                        accounts_subtitle.append(template.code)
                accounts_subtitle = ', '.join(accounts_subtitle)
            else:
                accounts_subtitle = ''

            if parties:
                parties_subtitle = []
                for party in parties:
                    if len(parties_subtitle) > 4:
                        parties_subtitle.append('...')
                        break
                    parties_subtitle.append(party.name)
                parties_subtitle = '; '.join(parties_subtitle)
            else:
                parties_subtitle = ''

        parameters = {}
        parameters['fiscal_year'] = companies[0]['fiscalyear'].name
        parameters['start_period'] = companies[0]['start_period'].name
        parameters['end_period'] = companies[0]['end_period'].name
        parameters['accounts'] = accounts_subtitle
        parameters['parties'] = parties_subtitle

        domain = [
            ('move.company', 'in', filter_companies),
            ]
        if account_templates:
            domain += [('account.template', 'in', account_templates)]
        else:
            with Transaction().set_context(active_test=False):
                account_templates = AccountTemplate.search([
                        ('parent', '!=', None),
                        ])

        domain += [('period', 'in', filter_periods)]

        parties_domain = []
        if parties:
            parties_domain = [
                'OR', [
                    ('account.kind', 'in', ['receivable', 'payable']),
                    ('party', 'in', [p.id for p in parties])],
                [
                    ('account.kind', 'not in', ['receivable', 'payable'])
                ]]
            domain.append(parties_domain)

        lines = Line.search(domain)
        line_ids = []
        if lines:
            cursor = Transaction().cursor
            cursor.execute("""
                SELECT
                    aml.id
                FROM
                    account_move_line aml,
                    account_move am,
                    account_account aa
                WHERE
                    am.id = aml.move AND
                    aa.id = aml.account AND
                    aml.id in (%s)
                ORDER BY
                    aa.template,
                    -- Sort by party only when account is of
                    -- type 'receivable' or 'payable'
                    CASE WHEN aa.kind in ('receivable', 'payable') THEN
                           aml.party ELSE 0 END,
                    am.date,
                    am.description,
                    aml.id
                """ % ','.join([str(x.id) for x in lines]))
            line_ids = [x[0] for x in cursor.fetchall()]

        records = []
        sequence = 0
        for line in Line.browse(line_ids):
            if line.account.kind in ('receivable', 'payable'):
                currentKey = (line.account.template, line.party and line.party
                    or None)
            else:
                currentKey = line.account.template
            sequence += 1
            records.append({
                    'sequence': sequence,
                    'company': line.move.company.rec_name,
                    'key': str(currentKey),
                    'account_code': line.account.code or '',
                    'account_name': line.account.name or '',
                    'account_type': line.account.kind,
                    'date': line.date.strftime('%d/%m/%Y'),
                    'move_line_name': line.description or '',
                    'ref': (line.origin.rec_name if line.origin and
                        hasattr(line.origin, 'rec_name') else ''),
                    'move_number': line.move.number,
                    'move_post_number': (line.move.post_number
                        if line.move.post_number else ''),
                    'party_name': line.party.name if line.party else '',
                    'credit': line.credit,
                    'debit': line.debit,
                    })
        return records, parameters

    @classmethod
    def execute(cls, ids, data):
        with Transaction().set_context(active_test=False):
            records, parameters = cls.prepare(data)
        return super(GeneralLedgerReport, cls).execute(ids, {
                'name': 'account_jasper_reports_multicompany.general_ledger',
                'model': 'account.move.line',
                'data_source': 'records',
                'records': records,
                'parameters': parameters,
                'output_format': data['output_format'],
                })
