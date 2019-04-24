# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from datetime import timedelta
from decimal import Decimal

from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateAction, Button
from trytond.pyson import Eval
from trytond.modules.jasper_reports.jasper import JasperReport
from trytond.i18n import gettext
from trytond.exceptions import UserWarning

__all__ = ['PrintGeneralLedgerStart',
    'PrintGeneralLedger', 'GeneralLedgerReport']


class PrintGeneralLedgerStart(ModelView):
    'Print General Ledger'
    __name__ = 'account_jasper_reports_multicompany.print_general_ledger.start'
    company = fields.Many2One('company.company', 'Base Company', required=True)
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
    companies = fields.Many2Many('company.company', None, None,
        'Other Companies', domain=[
            ('id', '!=', Eval('company')),
            ], depends=['company'])
    account_templates = fields.Many2Many('account.account.template', None,
        None, 'Accounts')
    parties = fields.Many2Many('party.party', None, None, 'Parties')
    output_format = fields.Selection([
            ('pdf', 'PDF'),
            ('xls', 'XLS'),
            ], 'Output Format', required=True)

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @fields.depends('company')
    def on_change_company(self):
        self.fiscalyear = None
        self.start_period = None
        self.end_period = None
        if self.company:
            FiscalYear = Pool().get('account.fiscalyear')
            self.fiscalyear = FiscalYear.find(self.company.id, exception=False)

    @classmethod
    def default_fiscalyear(cls):
        FiscalYear = Pool().get('account.fiscalyear')
        return FiscalYear.find(cls.default_company(), exception=False)

    @fields.depends('fiscalyear')
    def on_change_fiscalyear(self):
        self.start_period = None
        self.end_period = None

    @staticmethod
    def default_output_format():
        return 'pdf'


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

    def default_start(self, fields):
        pool = Pool()
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
            'account_templates': account_ids,
            'parties': party_ids,
            }

    def do_print_(self, action):
        pool = Pool()
        FiscalYear = pool.get('account.fiscalyear')
        Period = pool.get('account.period')

        data = {
            'companies': [{
                    'company': self.start.company.id,
                    'fiscalyear': self.start.fiscalyear.id,
                    'start_period': self.start.start_period.id,
                    'end_period': self.start.end_period.id,
                    }],
            'account_templates': [x.id for x in self.start.account_templates],
            'parties': [x.id for x in self.start.parties],
            'output_format': self.start.output_format,
            }
        for company in self.start.companies:
            fiscalyears = FiscalYear.search([
                    ('company', '=', company.id),
                    ('code', '=', self.start.fiscalyear.code)
                    if self.start.fiscalyear.code
                    else ('name', '=', self.start.fiscalyear.name),
                    ])
            if not fiscalyears:
                raise UserWarning(
                    'missing_fiscalyear_%s_%s' % (
                        company.id, self.start.fiscalyear.id),
                    gettext(
                        'account_jasper_reports_multicompany.missing_fiscalyear_multicompany',
                        company=company.rec_name,
                        fiscalyear=(self.start.fiscalyear.code
                            if self.start.fiscalyear.code
                            else self.start.fiscalyear.name),
                    ))
                continue

            start_periods = Period.search([
                    ('fiscalyear', '=', fiscalyears[0]),
                    ('code', '=', self.start.start_period.code)
                    if self.start.start_period.code
                    else ('name', '=', self.start.start_period.name),
                    ])
            if not start_periods:
                raise UserWarning(
                    'missing_period_%s_%s' % (company.id, fiscalyears[0].id),
                    gettext(
                    'account_jasper_reports_multicompany.missing_period_multicompany',
                        company=company.rec_name,
                        fiscalyear=fiscalyears[0].rec_name,
                        period=(self.start.start_period.code
                            if self.start.start_period.code
                            else self.start.start_period.name),
                    ))
                continue

            end_periods = Period.search([
                    ('fiscalyear', '=', fiscalyears[0]),
                    ('code', '=', self.start.end_period.code)
                    if self.start.end_period.code
                    else ('name', '=', self.start.end_period.name),
                    ])
            if not end_periods:
                raise UserWarning(
                    'missing_period_%s_%s' % (company.id, fiscalyears[0].id),
                    gettext(
                        'account_jasper_reports_multicompany.missing_period_multicompany',
                        company=company.rec_name,
                        fiscalyear=fiscalyears[0].rec_name,
                        period=(self.start.end_period.code
                            if self.start.end_period.code
                            else self.start.end_period.name),
                    ))
                continue

            data['companies'].append({
                'company': company.id,
                'fiscalyear': fiscalyears[0].id,
                'start_period': start_periods[0].id,
                'end_period': end_periods[0].id,
                })
        return action, data

    def transition_print_(self):
        return 'end'


class GeneralLedgerReport(JasperReport):
    __name__ = 'account_jasper_reports_multicompany.general_ledger'

    @classmethod
    def prepare(cls, data):
        pool = Pool()
        Account = pool.get('account.account')
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
                'OR', ['OR', [
                    ('account.type.receivable', '=', True),
                    ('account.type.payable', '=', True)],
                    ('party', 'in', [p.id for p in parties])],
                [
                    ('account.type.receivable', '=', False),
                    ('account.type.payable', '=', False)],
                ]
            domain.append(parties_domain)

        lines = Line.search(domain)
        line_ids = []
        if lines:
            cursor = Transaction().connection.cursor()
            cursor.execute("""
                SELECT
                    aml.id
                FROM
                    account_move_line aml,
                    account_move am,
                    account_account aa,
                    account_account_type at
                WHERE
                    am.id = aml.move AND
                    aa.id = aml.account AND
                    aa.type = at.id AND
                    aml.id in (%s)
                ORDER BY
                    am.company,
                    aml.account,
                    -- Sort by party only when account is of
                    -- type 'receivable' or 'payable'
                    CASE WHEN at.receivable == true or at.payable == true THEN
                           aml.party ELSE 0 END,
                    am.date,
                    am.description,
                    aml.id
                """ % ','.join([str(x.id) for x in lines if x]))
            line_ids = [x[0] for x in cursor.fetchall()]

        initial_balance_date = start_period.start_date - timedelta(days=1)
        init_values = {}
        init_party_values = {}
        for company_data in companies:
            accounts = Account.search([
                    ('company', '=', company_data['company']),
                    ('template', 'in', account_templates),
                    ])
            with Transaction().set_context(
                    company=company_data['company'].id,
                    date=initial_balance_date):
                init_values.update(
                    Account.read_account_vals(accounts,
                        with_moves=True,
                        exclude_party_moves=True))
            with Transaction().set_context(
                    company=company_data['company'].id,
                    date=initial_balance_date):
                init_party_values.update(
                    Party.get_account_values_by_party(parties, accounts, company_data['company']))

        records = []
        lastKey = None
        sequence = 0
        for line in Line.browse(line_ids):
            if line.account.type.receivable or line.account.type.payable:
                currentKey = (
                    line.move.company,
                    line.account,
                    line.party if line.party else None)
            else:
                currentKey = (
                    line.move.company,
                    line.account)

            if lastKey != currentKey:
                lastKey = currentKey
                if len(currentKey) == 3:
                    account_id = currentKey[1].id
                    party_id = currentKey[2].id if currentKey[2] else None
                else:
                    account_id = currentKey[1].id
                    party_id = None
                if party_id:
                    balance = init_party_values.get(account_id,
                        {}).get(party_id, {}).get('balance', Decimal(0))
                else:
                    balance = init_values.get(account_id, {}).get('balance',
                        Decimal(0))
            balance += line.debit - line.credit

            sequence += 1
            account_type = 'payable'
            if line.account.type.receivable:
                account_type = 'receivable'
            elif line.account.type.expense:
                account_type = 'expense'
            elif line.account.type.revenue:
                account_type = 'revenue'

            records.append({
                    'sequence': sequence,
                    'company': currentKey[0].rec_name,
                    'key': str(currentKey),
                    'account_code': line.account.code or '',
                    'account_name': line.account.name or '',
                    'account_type': account_type,
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
                    'balance': balance,
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
