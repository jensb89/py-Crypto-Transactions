from pandas.core.frame import DataFrame
from pyCryptoTransactions.Transaction import TransactionList
from pyCryptoTransactions.exporters.default import ExporterDefault
import datetime

#TODO: NOT VERY PYTHONIC, NEEDS IMPROVEMENT

class KoinlyExporter(ExporterDefault):

    def __init__(self, txData: TransactionList) -> None:
        super().__init__(txData)
        self.parseTxs()

    def parseTxs(self):
        data = []
        for tx in self.txData:
            
            #Only fee
            if tx.posIn.amount == 0 and tx.posOut.amount == 0 and tx.fee.amount != 0:
                entry = {"Date":datetime.datetime.strftime(tx.datetime, "%Y-%m-%d %H:%M"),
                        "Sent Amount":tx.fee.amount,
                        "Sent Currency":tx.fee.currency,
                        "Received Amount": "",
                        "Received Currency": "",
                        "Fee Amount":"",  #only show fee for trades
                        "Fee Currency":"",
                        "Net Worth Amount": "",
                        "Net Worth Currency": "",
                        "Label": "fee cost",
                        "Description": tx.note,
                        "TxHash":tx.txHash}
                data.append(entry)

            # In transaction with fee (e.g. Serum Dex)
            elif tx.posIn.amount != 0 and tx.posOut.amount == 0 and tx.fee.amount != 0:
                #create two entries, one for the fee as a cost
                entry = {"Date":datetime.datetime.strftime(tx.datetime, "%Y-%m-%d %H:%M"),
                        "Sent Amount":tx.fee.amount,
                        "Sent Currency":tx.fee.currency,
                        "Received Amount":"",
                        "Received Currency":"",
                        "Fee Amount":"",  #only show fee for trades
                        "Fee Currency":"",
                        "Net Worth Amount": "",
                        "Net Worth Currency": "",
                        "Label": "fee cost",
                        "Description": tx.note,
                        "TxHash":tx.txHash}
                entry2 = entry.copy()
                entry2["Received Amount"] = tx.posIn.amount
                entry2["Received Currency"] = tx.posIn.currency
                entry2["Sent Amount"] = ""
                entry2["Sent Currency"] = ""
                entry2["Label"] = tx.category
                data.append(entry)
                data.append(entry2)
            
            # Out transaction with a fee
            elif tx.posIn.amount == 0 and tx.posOut.amount != 0 and tx.fee.amount != 0:
                entry = {"Date":datetime.datetime.strftime(tx.datetime, "%Y-%m-%d %H:%M"),
                        "Sent Amount":tx.fee.amount,
                        "Sent Currency":tx.fee.currency,
                        "Received Amount":"",
                        "Received Currency":"",
                        "Fee Amount":"",  #only show fee for trades
                        "Fee Currency":"",
                        "Net Worth Amount": "",
                        "Net Worth Currency": "",
                        "Label": "fee  cost",
                        "Description": tx.note,
                        "TxHash":tx.txHash}
                entry2 = entry.copy()
                entry2["Sent Amount"] = tx.posOut.amount
                entry2["Sent Currency"] = tx.posOut.currency
                entry2["Label"] = tx.category
                data.append(entry)
                data.append(entry2)

            # In transaction without fee or out transaction without fee OR TRADE with fee
            #elif tx.posIn.amount != 0 or tx.posOut.amount !=0 and tx.fee.amount == 0 and (tx.posIn.amount == 0 or tx.posOut.amount == 0):
            else:
                entry = {"Date":datetime.datetime.strftime(tx.datetime, "%Y-%m-%d %H:%M"),
                        "Sent Amount":tx.posOut.amount if tx.posOut.amount!=0 else "",
                        "Sent Currency":tx.posOut.currency if tx.posOut.amount!=0 else "",
                        "Received Amount":tx.posIn.amount if tx.posIn.amount!=0  else "",
                        "Received Currency":tx.posIn.currency if tx.posIn.amount!=0 else "",
                        "Fee Amount":tx.fee.amount if tx.posIn.amount!=0 and tx.posOut.amount!=0 and tx.fee.amount!= 0 else "",  #only show fee for trades
                        "Fee Currency":tx.fee.currency if tx.posIn.amount!=0 and tx.posOut.amount!=0 and tx.fee.amount!=0 else "",
                        "Net Worth Amount": "",
                        "Net Worth Currency": "",
                        "Label": tx.category,
                        "Description": tx.note,
                        "TxHash":tx.txHash
                        }
                data.append(entry)
        self.df = DataFrame(data)

