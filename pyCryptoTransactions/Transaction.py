import abc
import pandas as pd
import datetime
from decimal import Decimal
import numpy as np
import json

class Position(object):
    """ A position represents an amount and its currency. """

    def __init__(self, amount, currency):
        self.amount = amount
        self.currency = currency

    @property
    def amount(self) -> Decimal:
        """
        The position amount
        Returns:
            float: The position amount
        """
        return self.__amount
    
    @amount.setter
    def amount(self, amount):
        if not(isinstance(amount, Decimal)):
            if isinstance(amount,str):
                amount = Decimal(amount)
            else:
                amount = Decimal(str(amount))
        if amount.is_nan():
            return
        else:
            self.__amount = amount

    @property
    def currency(self) -> str:
        """
        The position currency.
        Returns:
            str: The name of the currency.
        """
        return self.__currency
    
    @currency.setter
    def currency(self, value:str):
        if not(isinstance(value, str)):
            value = str(value).upper()
        if value == "nan":
            return
        self.__currency = value.upper()
    
    def __add__(self, new):
        """
        Add two positions.
        Returns:
            Position object
        """
        if isinstance(new,Decimal) and new.is_nan():
            return self
        # Don't add two currencies if we already have a balance != 0
        if self.amount != 0:
            assert(new.currency == self.currency)
        amount = self.amount + new.amount
        return Position(amount, new.currency)
        #self.amount += new.amount
        #print("added:")
        #print(self.amount)
    
    def __eq__(self, __o: object) -> bool:
        """Overrides the default implementation"""
        if isinstance(__o, Position):
            return self.amount == __o.amount and self.currency == __o.currency
        return NotImplemented
    
    def __repr__(self):
        return ", ".join([str(self.amount),self.currency])


class Fee(Position):
    """ The fee of a transaction """
    pass


class Transaction(object):
    """
    Transaction Object
    """

    @property
    def datetime(self):
        """
        The date and time of the transaction
        Returns:
            datetime.datetime: The datetime of the transaction
        """
        return self.__datetime
    
    @datetime.setter
    def datetime(self, dateTime):
        if isinstance(dateTime, datetime.datetime):
            self.__datetime = dateTime
        elif isinstance(dateTime, str):
            if dateTime[-1] == "Z":
                dateTime = dateTime[:-1]
            try:
                self.__datetime = datetime.datetime.fromisoformat(dateTime)
            except ValueError:
                print("Iso Format not detected")
        
    @property
    def posIn(self):
        return self.__posIn
    
    @posIn.setter
    def posIn(self, posIn):
        self.__posIn = posIn

    @property
    def posOut(self):
        return self.__posOut
    
    @posOut.setter
    def posOut(self, posOut):
        self.__posOut = posOut

    @property
    def txHash(self):
        return self.__txHash
    
    @txHash.setter
    def txHash(self, hash):
        self.__txHash = hash

    @property
    def tradingPair(self):
        """
        A pair of currencies representing the trading direction
        Returns:
            tuple[Position, Position]: A tuple with two positions
        """
        return self.__tradingPair
    
    @tradingPair.setter
    def tradingPair(self, pair):
        assert len(pair) == 2, "No pair provided"
        self.__tradingPair = pair
    
    @property
    def price(self):
        """
        The price per coin in fiat currency.
        Returns:
            float: The price of a coin.
        """
        return self.__price
    
    @price.setter
    def price(self, value):
        self.__price = value

    @property
    def fee(self) -> Fee:
        """
        The trading fee
        Returns:
            Fee: The trading fee
        """
        return self.__fee
    
    @fee.setter
    def fee(self, feeValue):
        assert isinstance(feeValue, Fee), 'The fee has to be of type Fee.'
        self.__fee = feeValue

    @property
    def category(self) -> str:
        """
        The category
        """
        return self.__category
    
    @category.setter
    def category(self, value):
       self.__category = value

    @property
    def note(self) -> str:
        return self.__note

    @note.setter
    def note(self, value:str):
        self.__note = value

    @property
    def orderId(self) -> str:
        return self.__orderId

    @orderId.setter
    def orderId(self, value:str):
        self.__orderId = value
    
    def isMultiSend(self) -> bool:
        return self._isMultiSend
    
    def isOutBound(self) -> bool:
        return self.posOut is not None and self.posOut.amount > 0

    def __init__(self, dateTime = None,
                       price:Decimal = Decimal(0),
                       posIn:Position = Position(0,"EUR"),
                       posOut:Position = Position(0,"EUR"),
                       fee:Fee = Fee(0,"EUR"),
                       txHash:str = "",
                       category:str = "",
                       blockHeight:int = 0,
                       tradingPair:tuple = [None, None],
                       network:str = "",
                       wallet:str = ""):
        """
        Args:
            datetime (datetime):                        The trading time
            fee (Fee):                                  Amount of trading fee
            ...todo: extend
        """

        super().__init__()

        if dateTime == None:
            self.__datetime = datetime.datetime.now()
        else:
            self.datetime = dateTime
        self.__price = price
        self.posIn = posIn
        self.posOut = posOut
        self.txHash = txHash
        self.category = category
        self.blockHeight = blockHeight
        self.tradingPair = tradingPair
        self.network = network
        self.wallet = wallet
        self.note = ""

        self._isMultiSend = False

        #exchange info
        self.exchange = ""
        self.orderId = ""
        self.tradeId = ""
        self.memo = ""

        #DEX
        self.contractAddress = ""

        #Others
        self.fromAddress = ""
        self.toAddress = ""

        if fee is None:
            self.fee = Fee(0, "EUR")
        else:
            assert isinstance(fee, Fee), 'The fee has to be of type Fee.'
            self.fee = fee

    def __repr__(self):
        return ", ".join([self.datetime.strftime("%Y/%m/%d, %H:%M:%S"),
                          str(self.posIn.amount) if self.posIn else "NONE",
                          self.posIn.currency,
                          str(self.posOut.amount) if self.posOut else "NONE",
                          self.posOut.currency,
                          self.txHash,
                          #self.trading_pair[0],
                          #self.trading_pair[1],
                          #str(self.price),
                          str(self.fee.amount),
                          self.fee.currency, self.note])
    
    def asDict(self):
        d = dict()
        d["Date"] = self.datetime 
        d["Sent Amount"] = self.posOut.amount if self.posOut.amount != 0 else None
        d["Sent Currency"] = self.posOut.currency if self.posOut.amount != 0 else ""
        d["Received Amount"] = self.posIn.amount if self.posIn.amount != 0 else None
        d["Received Currency"] = self.posIn.currency if self.posIn.amount != 0 else ""
        d["Fee Amount"] = self.fee.amount if self.fee.amount != 0 else None
        d["Fee Currency"] = self.fee.currency if self.fee.amount != 0 else ""
        d["TxHash"] = self.txHash
        d["Wallet"] = self.wallet
        d["Network"] = self.network
        d["Block Height"] = self.blockHeight
        d["Memo"] = self.memo
        d["Label"] = self.category
        d["Description"] = self.note
        d["fromAddress"] = self.fromAddress
        d["toaddress"] = self.toAddress
        d["exchange"] = self.exchange
        d["orderId"] = self.orderId

        return d

    def combinePositions(self, t):
        if not(isinstance(t, Transaction)):
            return NotImplemented
        if self.posIn.amount == 0 and t.posIn.amount != 0:
            self.posIn = t.posIn 
        if self.posOut.amount == 0 and t.posOut.amount != 0:
            self.posOut = t.posOut
        # todo; check other fields as well
    
    def serialize(self, obj):
        """JSON serializer for objects not serializable by default json code"""
        if isinstance(obj, datetime.datetime):
            serial = obj.isoformat()
            return serial

        if isinstance(obj, Decimal):
            serial = str(obj)
            return serial

        return obj.__dict__
    
    def toJSON(self):
        return json.dumps(self, default=lambda o: self.serialize(o), 
            sort_keys=True, indent=4)

class TransactionList(list):
    def __init__(self):

        super().__init__()

    def hasTx(self, txHash):
        for transaction in self:
            if transaction.txHash == txHash:
                return True
        return False
    
    def fromTxHash(self, txHash):
        for idx,transaction in enumerate(self):
            if transaction.txHash == txHash:
                return transaction,idx
        return None
    
    def fromOrderId(self, orderId):
        for idx,transaction in enumerate(self):
            if transaction.orderId == orderId:
                return transaction,idx
        return None
    
    def fromTradeId(self, tradeId):
        for idx,transaction in enumerate(self):
            if transaction.tradeId == tradeId:
                return transaction,idx
        return None
    
    def toPandasDataframe(self):
        data = []

        for elem in self:
            if elem is not None:
                data.append(elem.asDict())

        df = pd.DataFrame(data)

        return df
    
    def calculateBalance(self):
        balance = dict()
        for asset in self.getAssetList():
            amount = Decimal(0)
            for tx in self:
                amount += tx.posIn.amount if tx.posIn.currency == asset else 0
                amount -= tx.posOut.amount if tx.posOut.currency == asset else 0
                amount -= tx.fee.amount if tx.fee.currency == asset else 0
            if amount != 0 and not(amount.is_nan()):
                balance[asset] = amount
        return balance

    def getAssetList(self):
        df = self.toPandasDataframe()
        assetsIn = df["Sent Currency"].unique()
        assetsOut = df["Received Currency"].unique()
        assetsFee = df["Fee Currency"].unique()
        assets = np.concatenate((assetsIn,assetsOut,assetsFee),axis=None)
        assets = np.unique(assets)
        return assets

    def getLedger(self, coin):
        for tx in self:
            if tx.posIn.currency == coin and tx.posIn.amount > 0:
                print("{}:      {}".format(tx.datetime, tx.posIn.amount))
            if tx.posOut.currency == coin and tx.posOut.amount > 0:
                print("{}:     {}".format(tx.datetime, -tx.posOut.amount))
            if tx.fee.currency == coin and tx.fee.amount > 0:
                print("{}:     {}".format(tx.datetime, -tx.fee.amount))
    
    def toFile(self, filename):
        out = "[" + ','.join(item.toJSON() for item in self) + ']'
        with open(filename, "w") as outfile:
            outfile.write(out)
        



    