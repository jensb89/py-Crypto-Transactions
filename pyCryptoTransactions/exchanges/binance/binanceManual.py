from numpy import True_, inf
from pandas.core.frame import DataFrame
from pyCryptoTransactions.Importer import Importer
from pyCryptoTransactions.Transaction import Position, Transaction, TransactionList, Fee
from decimal import Decimal
import pandas as pd
import pytz
import datetime
import re
from copy import deepcopy

local = pytz.timezone("Europe/Berlin")
localUTC = pytz.utc

class BinanceManual(Importer):

    def __init__(self):
        super().__init__()
        self._apiAdress = "https://api.binance.com/api/v3/exchangeInfo"
        #https://api.binance.com/api/v3/exchangeInfo?symbol=BNBBTC
        self.exchangeInfo = None
        self._initRequest()
        self._getExchangeInfo()
    
    def _getExchangeInfo(self):
        data= self._request('')
        self.exchangeInfo = data

    def parseBuyHistory(self, excelFile):
        pass

    def _loadExcelFile(self, excelFile):
        df = pd.read_excel(excelFile)
        headers = list(df)
        return df, headers

    def parseDepositCryptoHistory(self, excelFile) -> TransactionList:
        return self.__parseDepsitWithdrawalCryptoHistory(excelFile, deposit=True)
    
    def parseWithdrawalCryptoHistory(self, excelFile) -> TransactionList:
        return self.__parseDepsitWithdrawalCryptoHistory(excelFile, deposit=False)

    def __parseDepsitWithdrawalCryptoHistory(self, excelFile, deposit:bool=True) -> TransactionList:
        df, headers = self._loadExcelFile(excelFile)
        tmpList = TransactionList()

        for index, row in df.iterrows():
            if not(self._checkStatus(row["Status"])):
                continue
            time = self._getDatetime(row[headers[0]], headers[0])
            if deposit:
                t = Transaction(dateTime=time, 
                                posIn=Position( Decimal(str(row["Amount"])), row["Coin"] ),
                                txHash=row["TXID"])
                t.fromAddress = row["Address"]
            else:
                t = Transaction(dateTime=time, 
                                posOut=Position( Decimal(str(row["Amount"])), row["Coin"] ),
                                fee = Fee( Decimal(str(row["TransactionFee"])), row["Coin"]),
                                txHash=row["TXID"])
                t.toAddress = row["Address"]
            tmpList.append(t)

        self.txList += tmpList
        return tmpList
    
    def parseDepositFiatHistory(self, excelFile) -> TransactionList:
        df, headers = self._loadExcelFile(excelFile)
        tmpList = TransactionList()

        for index, row in df.iterrows():
            if not(self._checkStatus(row["Status"])):
                continue
            time = self._getDatetime(row[headers[0]], headers[0])
            t = Transaction(dateTime=time, 
                            posIn=Position( Decimal(str(row["Indicated Amount"])), row["Coin"] ),
                            fee=Fee( Decimal(str(row["Fee"])), row["Coin"] ))
            t.orderId = row["Order ID"]
            t.note = "Deposit by " + row["Payment Method"]
            tmpList.append(t)

        self.txList += tmpList
        return tmpList

    def parseBuyCryptoHistory(self, excelFile) -> TransactionList:
        df, headers = self._loadExcelFile(excelFile)
        tmpList = TransactionList()

        for index, row in df.iterrows():
            if not(self._checkStatus(row["Status"])):
                continue
            time = self._getDatetime(row[headers[0]], headers[0])

            amountOut, currencyOut = self._getAmountCurrency(str(row["Amount"]))
            amountIn, currencyIn = self._getAmountCurrency(str(row["Final Amount"]))
            fee, feeCurrency = self._getAmountCurrency(str(row["Fees"]))

            if row["Method"] != "Cash Balance":
                # Make deposit
                tDeposit = Transaction(dateTime=time, posIn=Position( amountOut, currencyOut) )
                tDeposit.note = "Deposit for Crypto Buy with " + row["Method"]
                tmpList.append(tDeposit)

            t = Transaction(dateTime=time, 
                            posIn=Position( amountIn, currencyIn),
                            posOut=Position( amountOut - fee if currencyOut==feeCurrency else amountOut, currencyOut),
                            fee=Fee( fee, feeCurrency))
            t.orderId = row["Transaction ID"]
            tmpList.append(t)

        self.txList += tmpList
        return tmpList
    
    def parseTradeHistory(self, excelFile) -> TransactionList:
        df, headers = self._loadExcelFile(excelFile)
        tmpList = TransactionList()
        for index, row in df.iterrows():
            t = Transaction(dateTime=self._getDatetime(row[headers[0]], headers[0]))
            market = row["Market"]
            baseAsset, quoteAsset = self._getAssetsFromMarket(market)
            amount = Decimal( str(row["Amount"]) )
            total = Decimal( str(row["Total"]) )
            if row["Type"].lower() == "buy":
                posIn = Position( amount, baseAsset )
                posOut = Position( total, quoteAsset )
            elif row["Type"].lower() == "sell":
                posOut = Position( amount, baseAsset )
                posIn = Position( total, quoteAsset )
            else:
                continue
            t.posIn = posIn
            t.posOut = posOut
            t.fee = Fee( Decimal(str(row["Fee"])), row["Fee Coin"] )
            tmpList.append(t)

        self.txList += tmpList
        return tmpList

        #tpye = buy --> posIn
        #market = LUNAEUR ---> try to split ...  --> LUNA EUR 
        # BUY: posIn = "Amount" LUNA, posOut = "Total" EUR
        # SELL: posOut = "Amount" LUNA, posIn = "TOTAL" EUR 
        # +Fee
    
    def _getAssetsFromMarket(self, market:str):
        if self.exchangeInfo is None:
            raise BaseException("Exchange Info to match markets is not available")
        
        if not "symbols" in self.exchangeInfo:
            raise BaseException("No symbols found in exchange info")
        
        for info in self.exchangeInfo["symbols"]:
            if info["symbol"] == market:
                baseAsset = info["baseAsset"]
                quoteAsset = info["quoteAsset"]
                return baseAsset,quoteAsset
        return None

    
    def parseStatements(self, csvFile) -> TransactionList:
        df = self._loadStatementsCsv(csvFile)
        self.txList += self._parseStatementBNBVault(df)
        self.txList += self._parseStatementLaunchpoolInterest(df)
        self.txList += self._parseStatementSavingsInterest(df)
        self.txList += self._parseStatementPosSavingsInterest(df)
        self.txList += self._parseStatementsCommision(df)
        self.txList += self._parseStatementLiquiditySwapRewards(df)
        self.txList += self._parseStatementLiquidtiyAdd(df)
        self.txList += self._parseStatementDistribution(df)
        self.txList += self._parseStatementETH2StakingRewards(df)
        self.txList += self._parseStatementETH2Staking(df)
        self.txList += self._parseStatementLaunchpadTokenDistribution(df)
        self.txList += self._parseStatementLaunchpadSubscribe(df)
        

    def _parseStatementTrades(self, csvFile):
        n = pd.read_csv(csvFile,sep=";")
        tmp = n.copy()
        tmp.UTC_Time = tmp.UTC_Time.dt.round("10s")
        #print(tmp)
        uniqueDates = tmp.UTC_Time.unique()
        for date in uniqueDates:
            #print(date)
            self.__parsteTradesFromStatements(tmp.loc[tmp['UTC_Time'] == date])

    def __parsteTradesFromStatements(self, dataFrame):
        feeCoins =  dataFrame.loc[dataFrame['Operation'] == 'Fee', 'Coin'].unique()
        buyCoins = dataFrame.loc[dataFrame['Operation'] == 'Buy', 'Coin'].unique()
        sellCoins = dataFrame.loc[dataFrame['Operation'] == 'Sell', 'Coin'].unique()
        transactionRelatedCoins = dataFrame.loc[dataFrame['Operation'] == 'Transaction Related', 'Coin'].unique()
        
        # Calculate Fee
        if len(feeCoins)>1:
            print("ERROR: MORE THAN 1 fee Units")
            print(dataFrame.UTC_Time.unique())
        feeCoin = feeCoins[0] if feeCoins.size>0 else None
        totalFee = dataFrame.loc[dataFrame['Operation'] == 'Fee', 'Change'].sum()
        
        # Get all Buy Coins
        b = {}
        for coin in buyCoins:
            b[coin] = dataFrame.loc[(dataFrame['Operation'] == 'Buy') & (dataFrame['Coin'] == coin), 'Change'].sum()
            
        # Get all sell coins
        s = {}
        for coin in sellCoins:
            s[coin] = dataFrame.loc[(dataFrame['Operation'] == 'Sell') & (dataFrame['Coin'] == coin), 'Change'].sum()
        
        # Get all transaction related coins
        t = {}
        for coin in transactionRelatedCoins:
            t[coin] = dataFrame.loc[(dataFrame['Operation'] == 'Transaction Related') & (dataFrame['Coin'] == coin), 'Change'].sum()
        
        # Create Trades
        if len(t) == 1 and len(t)==1 and t[coin]<0 and b[buyCoins[0]]>0 and len(s)==0:
            totalBuy = b[buyCoins[0]]
            print("Trade: {:.4f}{} for {:.4f}{} (fee {:.4f}{})".format(totalBuy, buyCoins[0], t[coin], coin, totalFee, feeCoin))
        elif len(t) == 2 and buyCoins.size==0:
            coin1 = transactionRelatedCoins[0]
            coin2 = transactionRelatedCoins[1]
            buyCoin = coin1 if t[coin1] > 0 else coin2
            sellCoin = coin1 if t[coin1] < 0 else coin2
            if buyCoin == sellCoin:
                print("ERROR: SAME COIN IN TRADE")
            totalBuy = t[buyCoin]
            totalSell = t[sellCoin]
            print("Trade: {:.4f}{} for {:.4f}{} (fee {:.4f}{})".format(totalBuy, buyCoin, totalSell, sellCoin, totalFee, feeCoin))
        elif len(t) == 0 and buyCoins.size==2:
            coin1 = buyCoins[0]
            coin2 = buyCoins[1]
            buyCoin = coin1 if b[coin1] > 0 else coin2
            sellCoin = coin1 if b[coin1] < 0 else coin2
            if buyCoin == sellCoin:
                print("ERROR: SAME COIN IN TRADE")
            totalBuy = b[buyCoin]
            totalSell = b[sellCoin]
            print("Trade: {:.4f}{} for {:.4f}{} (fee {:.4f}{})".format(totalBuy, buyCoin, totalSell, sellCoin, totalFee, feeCoin))
        elif len(s) == 2 and len(t) == 0 and len(b) == 0:
            coin1 = sellCoins[0]
            coin2 = sellCoins[1]
            buyCoin = coin1 if s[coin1] > 0 else coin2
            sellCoin = coin1 if s[coin1] < 0 else coin2
            if buyCoin == sellCoin:
                print("ERROR: SAME COIN IN TRADE")
            totalBuy = s[buyCoin]
            totalSell = s[sellCoin]
            print("Trade: {:.4f}{} for {:.4f}{} (fee {:.4f}{})".format(totalBuy, buyCoin, totalSell, sellCoin, totalFee, feeCoin))
        elif len(t) == 0 and buyCoins.size==0:
            foo = 1
        else:
            print("NOT RECOGNIZED")
            print(len(t))
            print(len(b))
            print(b[buyCoins[0]])
            print(dataFrame.UTC_Time.unique())
            
        # todo: 2 buys (- and +)
        # todo: 2 sells (- and +)

    def _parseStatementBNBSmallAssetConvert(self, csvFile):
        df = pd.read_csv(csvFile,sep=";")
        df = df.loc[df['Operation'] == 'Small Assets Exchange BNB']
        return NotImplemented
    
    def _parseStatementBNBVault(self, df:DataFrame) -> TransactionList:
        return self.__parseStatementInOrOut(df, "Super BNB Mining", "Mining")
    
    def _parseStatementSavingsInterest(self, df:DataFrame) -> TransactionList:
        return self.__parseStatementInOrOut(df, "Savings Interest", "Income")
    
    def _parseStatementPosSavingsInterest(self, df:DataFrame) -> TransactionList:
        return self.__parseStatementInOrOut(df, "POS Savings Interest", "Income")
    
    def _parseStatementsCommision(self, df:DataFrame) -> TransactionList:
        return self.__parseStatementInOrOut(df, "Commission History", "Income")
    
    def _parseStatementLaunchpoolInterest(self, df:DataFrame) -> TransactionList:
        return self.__parseStatementInOrOut(df, "Launchpool Interest", "Airdrop")
    
    def _parseStatementLiquiditySwapRewards(self, df:DataFrame) -> TransactionList:
        return self.__parseStatementInOrOut(df, "Liquid Swap rewards", "Lending Income")

    def _parseStatementDistribution(self, df:DataFrame) -> TransactionList:
        return self.__parseStatementInOrOut(df, "Distribution", "Income") # or bounty? #airdrop?

    def _parseStatementETH2StakingRewards(self, df:DataFrame) -> TransactionList:
        return self.__parseStatementInOrOut(df, "ETH 2.0 Staking Rewards", "Staking Income")

    def _parseStatementLiquidtiyAdd(self, df:DataFrame) -> TransactionList:
        return self.__parseStatementInOrOut(df, "Liquid Swap add", "Lending", inTx=False) 

    def _parseStatementLaunchpadTokenDistribution(self, df:DataFrame) -> TransactionList:
        return self.__parseStatementInOrOut(df, "Launchpad token distribution", "Bounty")
    
    def _parseStatementLaunchpadSubscribe(self, df:DataFrame) -> TransactionList:
        insAndOuts = self.__parseStatementInOrOut(df, "Launchpad subscribe", "")
        #return insAndOuts
        tmpList = TransactionList()
        for tx in insAndOuts:
            tx2 = deepcopy(tx)
            if tx2.posIn.amount < 0:
                tx2.posOut.amount = abs(tx2.posIn.amount)
                tx2.posOut.currency = tx2.posIn.currency
                tx2.posIn.amount = 0
                tx2.note = "Launchpad"
            tmpList.append(tx2)

                #todo: category
        return tmpList
    
    def _parseStatementETH2Staking(self, df:DataFrame) -> TransactionList:
        insAndOuts = self.__parseStatementInOrOut(df, "ETH 2.0 Staking", "")
        tmpList = TransactionList()
        for inTx in insAndOuts:
            for outTx in insAndOuts:
                if inTx.datetime == outTx.datetime and inTx.posIn.amount > 0 and outTx.posIn.amount < 0:
                    t = Transaction(dateTime=inTx.datetime, posIn=inTx.posIn, posOut=outTx.posOut)
                    t.note = "ETH 2.0 Staking"
                    insAndOuts.remove(inTx)
                    insAndOuts.remove(outTx)
                    tmpList.append(t)
        if insAndOuts:
            raise Exception("parseStatementETH2Staking: Not all ETH 2 staking transactions could be evaluated!")
        return tmpList

    
    def __parseStatementInOrOut(self, dataFrame:DataFrame, operationName:str, setCategory:str="", inTx:bool=True) -> TransactionList:
        """Simple in or out txs without fee"""
        df = dataFrame.copy()
        headers = list(df)
        v2 = False
        if headers[0] == "User_ID":
            v2 = True
        df = df.loc[df['Operation'] == operationName]
        txs = TransactionList()
        for idx, row in df.iterrows():
            time = self._getDatetime(row[headers[1] if v2 else headers[0]], headers[1] if v2 else headers[0])
            if inTx:
                t = Transaction(dateTime=time, posIn=Position( Decimal( str(row["Change"]) ), row["Coin"]))
            else:
                t = Transaction(dateTime=time, posOut=Position( abs(Decimal( str(row["Change"]) )), row["Coin"]))
            t.category = setCategory
            txs.append(t)
        
        return txs
    
    def _loadStatementsCsv(self, csvFile) -> DataFrame:
        df = pd.read_csv(csvFile,sep=";")
        # newer versions of the statements include the user id and use , as separator
        if len(df.columns) == 1:
            df = pd.read_csv(csvFile,sep=",")
            assert(len(df.columns) > 1)
        return df

    def _getDatetime(self, dateAsString:str, csvRowName:str) -> datetime.datetime:
        if not "date" in csvRowName.lower() and not "utc_time" in csvRowName.lower():
            raise BaseException("Non parseable header in Excel file!")
        
        # try to get UTC+1 information
        r = re.compile(r"Date\(UTC\+(\d)\)")
        m = r.match(csvRowName)
        if m:
            deltaHours = int(m.group(1))
        else:
            #print("not found")
            #print(csvRowName)
            deltaHours = 0
        
        d = datetime.datetime.fromisoformat(dateAsString)
        d = d - datetime.timedelta(hours=deltaHours)
        return d

    def _getAmountCurrency(self, amountStr:str):
        """Assuming 1234.56 COIN"""
        amount = Decimal(amountStr.split(" ")[0])
        currency = amountStr.split(" ")[1]
        return amount, currency
    
    def _checkStatus(self, status:str) -> bool:
        if status != "Successful" and status != "Completed":
            return False
        return True


    def getTransactions(self, time=None) -> TransactionList:
        self.txList.sort(key=lambda r: r.datetime)
        return self.txList


#POS savings purchase = Staking In               --------     wird vernachlässigt
#POS savings redemption = Staking Out            -------      dito
#POS savings interest = Staking Interest         

#Savings purchase                               -------- vernachlässigt
#Savings Principal redemption (LDBNB to BNB)    ######
#Savings Interest

#Commission History

#Super BNB Mining = Mining
#Launchpool Interest = Airdrop ?

#Liquid Swap add

#Small assets exchange BNB

#ETH 2.0 Staking
#Launchpad token distribution
#Liquid Swap rewards