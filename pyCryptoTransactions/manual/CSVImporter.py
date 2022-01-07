from datetime import date
from decimal import Decimal
import pandas as pd

from pyCryptoTransactions.Importer import Importer
from pyCryptoTransactions.Transaction import Position, Transaction, TransactionList, Fee

class CSVImporterDefault(Importer):
    
    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        self.df =  pd.read_csv(self.filename)
    
    def parseCSV(self):
        txs = TransactionList()
        #txs.fillFromDataframe(self.df)
        return txs
    
