from pyCryptoTransactions.Transaction import TransactionList
import pandas as pd

class ExporterDefault(object):

    def __init__(self, txData:TransactionList) -> None:
        super().__init__()
        self.txData = txData
        self.df = pd.DataFrame()

    def exportToCsv(self, outCsvFilename) -> None:
        self.df.to_csv(outCsvFilename)

    def exportToExcel(self, outExcelFilename) -> None:
        self.df.to_excel(outExcelFilename, index=False)
