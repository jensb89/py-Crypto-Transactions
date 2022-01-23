
from typing import Optional
from pandas.core.frame import DataFrame
from pyCryptoTransactions.Transaction import TransactionList
from pyCryptoTransactions.exporters.default import ExporterDefault
import datetime

class AccointingExporter(ExporterDefault):

    def __init__(self, txData: TransactionList) -> None:
        super().__init__(txData)
        self.parseTxs()

    def parseTxs(self):
        data = []
        for tx in self.txData:
            feeCost = False
            if tx.posIn.amount != 0 and tx.posOut.amount != 0:
                tType = "order"
            elif tx.posIn.amount != 0 and tx.posOut.amount == 0:
                tType = "deposit"
            elif tx.posIn.amount == 0 and tx.posOut.amount != 0:
                tType = "withdraw"
            elif tx.posIn.amount == 0 and tx.posOut.amount == 0 and tx.fee.amount != 0:
                feeCost = True
                tType = "withdraw"
            else:
                print("Accointing Export: Unknown type: Tx {}".format(tx.txHash))
                print(tx)
                continue
            
            if tx.category.lower() == "mining":
                classification = "mined"
            elif tx.category.lower() == "income":
                classification = "income"
            elif tx.category.lower() == "airdrop":
                classification = "airdrop" 
            elif tx.category.lower() == "lending income":
                classification = "lending_income"
            elif tx.category.lower() == "lending":
                classification = "lending"
            elif tx.category.lower() == "staking income" or tx.category.lower() == "staking":
                classification = "staked"
            elif tx.category.lower() == "bounty":
                classification = "bounty"
            else:
                classification = ""

            entry = {"transactionType":tType,
                    "date":datetime.datetime.strftime(tx.datetime, "%m/%d/%Y %H:%M:%S"),
                    "inBuyAmount": tx.posIn.amount if tx.posIn.amount != 0 else "",
                    "inBuyAsset": tx.posIn.currency if tx.posIn.amount != 0 else "",

                    "outSellAmount": tx.fee.amount if feeCost else (tx.posOut.amount if tx.posOut.amount != 0 else ""),
                    "outSellAsset": tx.fee.currency if feeCost else (tx.posOut.currency if tx.posOut.amount != 0 else ""),
                    "feeAmount (optional)": tx.fee.amount if tx.fee.amount >0 and not feeCost else "",
                    "feeAsset (optional)": tx.fee.currency if tx.fee.amount > 0 and not feeCost else "",

                    "classification (optional)": "fee" if feeCost else classification, #no support for now
                    "operationId (optional)": tx.txHash}
            data.append(entry)
        self.df = DataFrame(data)
    




#transactionType	date	inBuyAmount	inBuyAsset	outSellAmount	outSellAsset	feeAmount (optional)	feeAsset (optional)	classification (optional)	operationId (optional)

#intags:
#add funds	airdrop	bounty	
#gambling_income
#gift_received
#hard_fork	ignored	 
#income	lending_income	
#liquidity_pool
#margin_gain	master_node	mined	staked

#outTags:
#remove funds	payment	fee	gambling_used	gift_sent	ignored	interest_paid	 
#lending	lost	margin_fee	margin_loss	payment

#MM/DD/YYYY HH:mm:SS