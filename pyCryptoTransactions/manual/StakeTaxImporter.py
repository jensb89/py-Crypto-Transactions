from pyCryptoTransactions.Transaction import Transaction, TransactionList
from .CSVImporter import CSVImporterDefault

from copy import deepcopy

class StakeTaxImporter(CSVImporterDefault):
    """Imports exported files from stake.tax (default format)"""
    def __init__(self, filename):
        super().__init__(filename)

        self.mapProperties = {"timestamp":"datetime", 
                              "tx_type":"category",
                              "taxable":None,
                              "received_amount": "posIn.amount",
                              "received_currency": "posIn.currency",
                              "sent_amount": "posOut.amount",
                              "sent_currency": "posOut.currency",
                              "fee": "fee.amount",
                              "fee_currency":"fee.currency",
                              "comment": "note",
                              "txid":"txHash",
                              "url": None,
                              "exchange":"network",
                              "wallet_address":"wallet" }

    def parseFile(self):
        self.checkFields()
        assert len(self.mapProperties) == len(self.df.columns), "Wrong number of columns in the dataframe"

        #Remove _blockchain from network name:
        self.df["exchange"] = self.df["exchange"].str.replace("_blockchain","")

        txList = TransactionList()
        
        t = Transaction()
        for index, row in self.df.iterrows():
            tmp = deepcopy(t)
            for key, val in self.mapProperties.items():
                if val == None:
                    continue
                if val.find('.')!=-1:
                    parent, child = val.split('.')
                    setattr(getattr(tmp, parent), child, row[key])
                else:
                    setattr(tmp,val,row[key])
            txList.append(tmp)
            del tmp

        return txList

    def checkFields(self):
        for key in self.mapProperties:
            if key not in self.df:
                print("Warning: {} is not included in file {}".format(key, self.filename))
    
    def getTransactions(self, time=None) -> TransactionList:
        #return super().getTransactions(address, time=time)
        return self.parseFile()

