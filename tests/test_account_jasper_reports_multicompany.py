# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
from decimal import Decimal

import trytond.tests.test_tryton
from trytond.tests.test_tryton import test_view, test_depends
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT
from trytond.transaction import Transaction


class AccountJasperReportsMulticompanyTestCase(unittest.TestCase):
    'Test Account Jasper Reports Multicompany module'

    def setUp(self):
        trytond.tests.test_tryton.install_module(
            'account_jasper_reports_multicompany')
        self.account = POOL.get('account.account')
        self.company = POOL.get('company.company')
        self.party = POOL.get('party.party')
        self.party_address = POOL.get('party.address')
        self.fiscalyear = POOL.get('account.fiscalyear')
        self.move = POOL.get('account.move')
        self.journal = POOL.get('account.journal')
        self.print_general_ledger_company = POOL.get(
            'account_jasper_reports_multicompany.print_general_ledger.start')
        self.print_general_ledger = POOL.get(
            'account_jasper_reports_multicompany.print_general_ledger',
            type='wizard')
        self.general_ledger_report = POOL.get(
            'account_jasper_reports_multicompany.general_ledger',
            type='report')

    def test0005views(self):
        'Test views'
        test_view('account_jasper_reports_multicompany')

    def test0006depends(self):
        'Test depends'
        test_depends()

    def test0030general_ledger(self):
        'Test General Ledger'
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            # TODO: create two companies (and account chart, fiscal year...)
            self.create_moves()
            company, = self.company.search([
                    ('rec_name', '=', 'Dunder Mifflin')])
            fiscalyear, = self.fiscalyear.search([])
            period = fiscalyear.periods[0]
            last_period = fiscalyear.periods[-1]
            session_id, _, _ = self.print_general_ledger.create()
            print_general_ledger = self.print_general_ledger(session_id)
            print_general_ledger.start.companies = []
            print_general_ledger_company = self.print_general_ledger_company()
            print_general_ledger.start.companies.append(
                print_general_ledger_company)
            print_general_ledger_company.company = company
            print_general_ledger_company.fiscalyear = fiscalyear
            print_general_ledger_company.start_period = period
            print_general_ledger_company.end_period = last_period
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
            records, parameters = self.general_ledger_report.prepare(data)
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
            session_id, _, _ = self.print_general_ledger.create()
            print_general_ledger = self.print_general_ledger(session_id)
            print_general_ledger.start.companies = []
            print_general_ledger_company = self.print_general_ledger_company()
            print_general_ledger.start.companies.append(
                print_general_ledger_company)
            print_general_ledger_company.company = company
            print_general_ledger_company.fiscalyear = fiscalyear
            print_general_ledger_company.start_period = period
            print_general_ledger_company.end_period = period
            print_general_ledger.start.parties = []
            print_general_ledger.start.account_templates = []
            print_general_ledger.start.output_format = 'pdf'
            _, data = print_general_ledger.do_print_(None)
            records, parameters = self.general_ledger_report.prepare(data)
            self.assertEqual(len(records), 8)
            credit = sum([m['credit'] for m in records])
            debit = sum([m['debit'] for m in records])
            self.assertEqual(credit, debit)
            self.assertEqual(credit, Decimal('380.0'))
            dates = [r['date'] for r in records]
            for date in dates:
                self.assertEqual(date, period.start_date.strftime('%d/%m/%Y'))

            # Filtered by accounts
            expense, = self.account.search([
                    ('kind', '=', 'expense'),
                    ])
            session_id, _, _ = self.print_general_ledger.create()
            print_general_ledger = self.print_general_ledger(session_id)
            print_general_ledger.start.companies = []
            print_general_ledger_company = self.print_general_ledger_company()
            print_general_ledger.start.companies.append(
                print_general_ledger_company)
            print_general_ledger_company.company = company
            print_general_ledger_company.fiscalyear = fiscalyear
            print_general_ledger_company.start_period = period
            print_general_ledger_company.end_period = last_period
            print_general_ledger.start.parties = []
            print_general_ledger.start.account_templates = [
                expense.template.id]
            print_general_ledger.start.output_format = 'pdf'
            _, data = print_general_ledger.do_print_(None)
            records, parameters = self.general_ledger_report.prepare(data)
            self.assertEqual(
                parameters['accounts'], expense.template.code or '')
            self.assertEqual(len(records), 3)
            credit = sum([m['credit'] for m in records])
            debit = sum([m['debit'] for m in records])
            self.assertEqual(credit, Decimal('0.0'))
            self.assertEqual(debit, Decimal('130.0'))

            # Filter by parties
            customer1, = self.party.search([
                    ('name', '=', 'customer1'),
                    ])
            session_id, _, _ = self.print_general_ledger.create()
            print_general_ledger = self.print_general_ledger(session_id)
            print_general_ledger.start.companies = []
            print_general_ledger_company = self.print_general_ledger_company()
            print_general_ledger.start.companies.append(
                print_general_ledger_company)
            print_general_ledger_company.company = company
            print_general_ledger_company.fiscalyear = fiscalyear
            print_general_ledger_company.start_period = period
            print_general_ledger_company.end_period = last_period
            print_general_ledger.start.parties = [customer1.id]
            print_general_ledger.start.account_templates = []
            print_general_ledger.start.output_format = 'pdf'
            _, data = print_general_ledger.do_print_(None)
            records, parameters = self.general_ledger_report.prepare(data)
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
            receivable, = self.account.search([
                    ('kind', '=', 'receivable'),
                    ])
            session_id, _, _ = self.print_general_ledger.create()
            print_general_ledger = self.print_general_ledger(session_id)
            print_general_ledger.start.companies = []
            print_general_ledger_company = self.print_general_ledger_company()
            print_general_ledger.start.companies.append(
                print_general_ledger_company)
            print_general_ledger_company.company = company
            print_general_ledger_company.fiscalyear = fiscalyear
            print_general_ledger_company.start_period = period
            print_general_ledger_company.end_period = last_period
            print_general_ledger.start.parties = [customer1.id]
            print_general_ledger.start.account_templates = [
                receivable.template.id]
            print_general_ledger.start.output_format = 'pdf'
            _, data = print_general_ledger.do_print_(None)
            records, parameters = self.general_ledger_report.prepare(data)
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

    def create_moves(self, fiscalyear=None):
        'Create moves for running tests'
        if not fiscalyear:
            fiscalyear, = self.fiscalyear.search([])
        period = fiscalyear.periods[0]
        last_period = fiscalyear.periods[-1]
        journal_revenue, = self.journal.search([
                ('code', '=', 'REV'),
                ])
        journal_expense, = self.journal.search([
                ('code', '=', 'EXP'),
                ])
        chart, = self.account.search([
                ('parent', '=', None),
                ])
        revenue, = self.account.search([
                ('kind', '=', 'revenue'),
                ])
        revenue.parent = chart
        revenue.code = '7'
        revenue.save()
        receivable, = self.account.search([
                ('kind', '=', 'receivable'),
                ])
        receivable.parent = chart
        receivable.code = '43'
        receivable.save()
        expense, = self.account.search([
                ('kind', '=', 'expense'),
                ])
        expense.parent = chart
        expense.code = '6'
        expense.save()
        payable, = self.account.search([
                ('kind', '=', 'payable'),
                ])
        payable.parent = chart
        payable.code = '41'
        payable.save()
        self.account.create([{
                    'name': 'View',
                    'code': '1',
                    'kind': 'view',
                    'parent': chart.id,
                    }])
        #Create some parties if not exist
        if self.party.search([('name', '=', 'customer1')]):
            customer1, = self.party.search([('name', '=', 'customer1')])
            customer2, = self.party.search([('name', '=', 'customer2')])
            supplier1, = self.party.search([('name', '=', 'supplier1')])
            with Transaction().set_context(active_test=False):
                supplier2, = self.party.search([('name', '=', 'supplier2')])
        else:
            customer1, customer2, supplier1, supplier2 = self.party.create([{
                        'name': 'customer1',
                        }, {
                        'name': 'customer2',
                        }, {
                        'name': 'supplier1',
                        }, {
                        'name': 'supplier2',
                        'active': False,
                        }])
            self.party_address.create([{
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
        moves = self.move.create(vlist)
        self.move.post(moves)
        # Set account inactive
        expense.active = False
        expense.save()


def suite():
    suite = trytond.tests.test_tryton.suite()
    from trytond.modules.account.tests import test_account
    for test in test_account.suite():
        # Skip doctest
        class_name = test.__class__.__name__
        if test not in suite and class_name != 'DocFileCase':
            suite.addTest(test)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        AccountJasperReportsMulticompanyTestCase))
    return suite
