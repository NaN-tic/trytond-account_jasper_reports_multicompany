# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
from decimal import Decimal

import trytond.tests.test_tryton
from trytond.pool import Pool
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.transaction import Transaction

from trytond.modules.company.tests import create_company, set_company
from trytond.modules.account.tests import create_chart, get_fiscalyear
from trytond.modules.account_invoice.tests import set_invoice_sequences


class AccountJasperReportsMulticompanyTestCase(ModuleTestCase):
    'Test Account Jasper Reports Multicompany module'
    module = 'account_jasper_reports_multicompany'

    @with_transaction()
    def test0030general_ledger(self):
        'Test General Ledger'
        pool = Pool()
        Account = pool.get('account.account')
        Party = pool.get('party.party')
        PrintGeneralLedger = pool.get(
            'account_jasper_reports_multicompany.print_general_ledger',
            type='wizard')
        GeneralLedgerReport = pool.get(
            'account_jasper_reports_multicompany.general_ledger',
            type='report')

        # Create Company
        company = create_company()
        with set_company(company):

            # Create Chart of Accounts
            create_chart(company)

            # Create Fiscalyear
            fiscalyear = get_fiscalyear(company)
            fiscalyear = set_invoice_sequences(fiscalyear)
            fiscalyear.save()
            fiscalyear.create_period([fiscalyear])
            period = fiscalyear.periods[0]
            last_period = fiscalyear.periods[-1]

            self.create_moves(fiscalyear)

            session_id, _, _ = PrintGeneralLedger.create()
            print_general_ledger = PrintGeneralLedger(session_id)
            print_general_ledger.start.companies = []
            print_general_ledger.start.company = company
            print_general_ledger.start.on_change_company()
            print_general_ledger.start.start_period = period
            print_general_ledger.start.end_period = last_period
            print_general_ledger.start.parties = []
            print_general_ledger.start.account_templates = []
            print_general_ledger.start.output_format = 'pdf'
            _, data = print_general_ledger.do_print_(None)

            # Full general_ledger
            self.assertEqual(len(data['companies']), 1)
            self.assertEqual(data['companies'][0]['company'], company.id)
            self.assertEqual(data['companies'][0]['fiscalyear'], fiscalyear.id)
            self.assertEqual(data['companies'][0]['start_period'], period.id)
            self.assertEqual(
                data['companies'][0]['end_period'], last_period.id)
            self.assertEqual(len(data['account_templates']), 0)
            self.assertEqual(len(data['parties']), 0)
            self.assertEqual(data['output_format'], 'pdf')
            records, parameters = GeneralLedgerReport.prepare(data)
            self.assertEqual(len(records), 12)
            self.assertEqual(parameters['start_period'], period.name)
            self.assertEqual(parameters['end_period'], last_period.name)
            self.assertEqual(parameters['fiscal_year'], fiscalyear.name)
            self.assertEqual(parameters['accounts'], '')
            self.assertEqual(parameters['parties'], '')
            credit = sum([m['credit'] for m in records])
            debit = sum([m['debit'] for m in records])
            self.assertEqual(credit, debit)
            self.assertEqual(credit, Decimal('730.0'))
            with_party = [m for m in records if m['party_name'] != '']
            self.assertEqual(len(with_party), 6)
            dates = sorted(set([r['date'] for r in records]))
            for date, expected_value in zip(dates, [period.start_date,
                        last_period.end_date]):
                self.assertEqual(date, expected_value.strftime('%d/%m/%Y'))

            # Filtered by periods
            session_id, _, _ = PrintGeneralLedger.create()
            print_general_ledger = PrintGeneralLedger(session_id)
            print_general_ledger.start.companies = []
            print_general_ledger.start.company = company
            print_general_ledger.start.on_change_company()
            print_general_ledger.start.start_period = period
            print_general_ledger.start.end_period = period
            print_general_ledger.start.parties = []
            print_general_ledger.start.account_templates = []
            print_general_ledger.start.output_format = 'pdf'
            _, data = print_general_ledger.do_print_(None)
            records, parameters = GeneralLedgerReport.prepare(data)
            self.assertEqual(len(records), 8)
            credit = sum([m['credit'] for m in records])
            debit = sum([m['debit'] for m in records])
            self.assertEqual(credit, debit)
            self.assertEqual(credit, Decimal('380.0'))
            dates = [r['date'] for r in records]
            for date in dates:
                self.assertEqual(date, period.start_date.strftime('%d/%m/%Y'))

            # Filtered by accounts
            expense, = Account.search([
                    ('type.expense', '=', True),
                    ])
            session_id, _, _ = PrintGeneralLedger.create()
            print_general_ledger = PrintGeneralLedger(session_id)
            print_general_ledger.start.companies = []
            print_general_ledger.start.company = company
            print_general_ledger.start.on_change_company()
            print_general_ledger.start.start_period = period
            print_general_ledger.start.end_period = last_period
            print_general_ledger.start.parties = []
            print_general_ledger.start.account_templates = [
                expense.template.id]
            print_general_ledger.start.output_format = 'pdf'
            _, data = print_general_ledger.do_print_(None)
            records, parameters = GeneralLedgerReport.prepare(data)
            self.assertEqual(
                parameters['accounts'], expense.template.code or '')
            self.assertEqual(len(records), 3)
            credit = sum([m['credit'] for m in records])
            debit = sum([m['debit'] for m in records])
            self.assertEqual(credit, Decimal('0.0'))
            self.assertEqual(debit, Decimal('130.0'))

            # Filter by parties
            customer1, = Party.search([
                    ('name', '=', 'customer1'),
                    ])
            session_id, _, _ = PrintGeneralLedger.create()
            print_general_ledger = PrintGeneralLedger(session_id)
            print_general_ledger.start.companies = []
            print_general_ledger.start.company = company
            print_general_ledger.start.on_change_company()
            print_general_ledger.start.start_period = period
            print_general_ledger.start.end_period = last_period
            print_general_ledger.start.parties = [customer1.id]
            print_general_ledger.start.account_templates = []
            print_general_ledger.start.output_format = 'pdf'
            _, data = print_general_ledger.do_print_(None)
            records, parameters = GeneralLedgerReport.prepare(data)
            self.assertEqual(parameters['parties'], customer1.rec_name)
            self.assertEqual(len(records), 7)
            credit = sum([m['credit'] for m in records])
            debit = sum([m['debit'] for m in records])
            self.assertEqual(credit, Decimal('600.0'))
            self.assertEqual(debit, Decimal('230.0'))
            credit = sum([m['credit'] for m in records
                    if m['party_name'] != ''])
            debit = sum([m['debit'] for m in records
                    if m['party_name'] != ''])
            self.assertEqual(credit, Decimal('0.0'))
            self.assertEqual(debit, Decimal('100.0'))

            # Filter by parties and accounts
            receivable, = Account.search([
                    ('type.receivable', '=', True),
                    ])
            session_id, _, _ = PrintGeneralLedger.create()
            print_general_ledger = PrintGeneralLedger(session_id)
            print_general_ledger.start.companies = []
            print_general_ledger.start.company = company
            print_general_ledger.start.on_change_company()
            print_general_ledger.start.start_period = period
            print_general_ledger.start.end_period = last_period
            print_general_ledger.start.parties = [customer1.id]
            print_general_ledger.start.account_templates = [
                receivable.template.id]
            print_general_ledger.start.output_format = 'pdf'
            _, data = print_general_ledger.do_print_(None)
            records, parameters = GeneralLedgerReport.prepare(data)
            self.assertEqual(parameters['parties'], customer1.rec_name)
            self.assertEqual(parameters['accounts'],
                receivable.template.code or '')
            self.assertEqual(len(records), 1)
            credit = sum([m['credit'] for m in records])
            debit = sum([m['debit'] for m in records])
            self.assertEqual(credit, Decimal('0.0'))
            self.assertEqual(debit, Decimal('100.0'))
            self.assertEqual(True, all(m['party_name'] != ''
                    for m in records))

    def create_moves(self, fiscalyear):
        'Create moves for running tests'
        pool = Pool()
        Account = pool.get('account.account')
        Party = pool.get('party.party')
        Address = pool.get('party.address')
        Move = pool.get('account.move')
        Journal = pool.get('account.journal')

        period = fiscalyear.periods[0]
        last_period = fiscalyear.periods[-1]
        journal_revenue, = Journal.search([
                ('code', '=', 'REV'),
                ])
        journal_expense, = Journal.search([
                ('code', '=', 'EXP'),
                ])
        chart, = Account.search([
                ('parent', '=', None),
                ])
        revenue, = Account.search([
                ('type.revenue', '=', True),
                ])
        revenue.parent = chart
        revenue.code = '7'
        revenue.save()
        receivable, = Account.search([
                ('type.receivable', '=', True),
                ])
        receivable.parent = chart
        receivable.code = '43'
        receivable.save()
        expense, = Account.search([
                ('type.expense', '=', True),
                ])
        expense.parent = chart
        expense.code = '6'
        expense.save()
        payable, = Account.search([
                ('type.payable', '=', True),
                ])
        payable.parent = chart
        payable.code = '41'
        payable.save()
        Account.create([{
                    'name': 'View',
                    'code': '1',                    
                    'parent': chart.id,
                    }])

        # Create some parties if not exist
        if Party.search([('name', '=', 'customer1')]):
            customer1, = Party.search([('name', '=', 'customer1')])
            customer2, = Party.search([('name', '=', 'customer2')])
            supplier1, = Party.search([('name', '=', 'supplier1')])
            with Transaction().set_context(active_test=False):
                supplier2, = Party.search([('name', '=', 'supplier2')])
        else:
            customer1, customer2, supplier1, supplier2 = Party.create([{
                        'name': 'customer1',
                        }, {
                        'name': 'customer2',
                        }, {
                        'name': 'supplier1',
                        }, {
                        'name': 'supplier2',
                        'active': False,
                        }])
            Address.create([{
                            'active': True,
                            'party': customer1.id,
                        }, {
                            'active': True,
                            'party': supplier1.id,
                        }])

        # Create some moves
        vlist = [
            {
                'period': period.id,
                'journal': journal_revenue.id,
                'date': period.start_date,
                'lines': [
                    ('create', [{
                                'account': revenue.id,
                                'credit': Decimal(100),
                                }, {
                                'party': customer1.id,
                                'account': receivable.id,
                                'debit': Decimal(100),
                                }]),
                    ],
                },
            {
                'period': period.id,
                'journal': journal_revenue.id,
                'date': period.start_date,
                'lines': [
                    ('create', [{
                                'account': revenue.id,
                                'credit': Decimal(200),
                                }, {
                                'party': customer2.id,
                                'account': receivable.id,
                                'debit': Decimal(200),
                                }]),
                    ],
                },
            {
                'period': period.id,
                'journal': journal_expense.id,
                'date': period.start_date,
                'lines': [
                    ('create', [{
                                'account': expense.id,
                                'debit': Decimal(30),
                                }, {
                                'party': supplier1.id,
                                'account': payable.id,
                                'credit': Decimal(30),
                                }]),
                    ],
                },
            {
                'period': period.id,
                'journal': journal_expense.id,
                'date': period.start_date,
                'lines': [
                    ('create', [{
                                'account': expense.id,
                                'debit': Decimal(50),
                                }, {
                                'party': supplier2.id,
                                'account': payable.id,
                                'credit': Decimal(50),
                                }]),
                    ],
                },
            {
                'period': last_period.id,
                'journal': journal_expense.id,
                'date': last_period.end_date,
                'lines': [
                    ('create', [{
                                'account': expense.id,
                                'debit': Decimal(50),
                                }, {
                                'party': supplier2.id,
                                'account': payable.id,
                                'credit': Decimal(50),
                                }]),
                    ],
                },
            {
                'period': last_period.id,
                'journal': journal_revenue.id,
                'date': last_period.end_date,
                'lines': [
                    ('create', [{
                                'account': revenue.id,
                                'credit': Decimal(300),
                                }, {
                                'party': customer2.id,
                                'account': receivable.id,
                                'debit': Decimal(300),
                                }]),
                    ],
                },
            ]
        moves = Move.create(vlist)
        Move.post(moves)
        # Set account inactive
        expense.active = False
        expense.save()


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        AccountJasperReportsMulticompanyTestCase))
    return suite
