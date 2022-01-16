from pyCryptoTransactions import Importer
from pyCryptoTransactions.Transaction import TransactionList

class Wallet(object):

    def __init__(self, walletName) -> None:
        self.walletName = walletName
        self.importers = list[Importer.Importer]()

    def addNetworkImporter(self, importer:Importer) -> None:
        self.importers.append(importer)

    def getTxs(self) -> TransactionList:
        txs = TransactionList()
        for importer in self.importers:
            txs += importer.getTransactions()
        return txs