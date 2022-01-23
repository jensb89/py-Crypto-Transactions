from decimal import Decimal
from pyCryptoTransactions.Transaction import Position, Transaction,TransactionList, Fee
from pyCryptoTransactions.Importer import Importer

import iota #pip install pyota
import datetime
import pytz as timezone

class IotaImport(Importer):

    def __init__(self, address):
        super().__init__()
        self.address = iota.Address(address[0:81].upper())
        self.api = iota.Iota('https://nodes.iota.org:443')
        self.rawTxs = []

    def _findTransactions(self):
        response = self.api.find_transaction_objects(addresses=[self.address])
        if not response['transactions']:
            print('Couldn\'t find data for the given address.')
        else:
            self.rawTxs = response["transactions"]

    def getTransactions(self, time=None) -> TransactionList:
        self._findTransactions()
        for tx in self.rawTxs:
            if tx.value != 0:
                time = datetime.datetime.fromtimestamp(tx.timestamp, tz=timezone.utc)
                t = Transaction(dateTime=time)
                if tx.value > 0:
                    t.posOut = Position(Decimal(tx.value)/Decimal(1E6), "IOTA")
                else:
                    t.posIn = Position(Decimal(tx.value)/Decimal(1E6), "IOTA")
                t.txHash = tx.hash.as_json_compatible()
                self.txList.append(t)
        
        return self.txList