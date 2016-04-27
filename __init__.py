# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .general_ledger import *


def register():
    Pool.register(
        PrintGeneralLedgerStart,
        PrintGeneralLedgerCompany,
        module='account_jasper_reports_multicompany', type_='model')
    Pool.register(
        PrintGeneralLedger,
        module='account_jasper_reports_multicompany', type_='wizard')
    Pool.register(
        GeneralLedgerReport,
        module='account_jasper_reports_multicompany', type_='report')
