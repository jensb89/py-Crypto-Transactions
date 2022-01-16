from pyCryptoTransactions.Importer import Importer
from pyCryptoTransactions.Transaction import Position, Transaction, TransactionList, Fee
from pyCryptoTransactions.exchanges.coinbase.coinbaseApiWrapper import coinbase
from time import sleep
from decimal import Decimal

class CoinbaseImporter(Importer):
    def __init__(self, client_id, client_secret, redirect_url) -> None:
        super().__init__()
        
        self.client = self.authenticate(client_id, client_secret, redirect_url)
        self.accounts = []
        #self.getAllAccounts()
        self.rawTxs = []
        self._trades = TransactionList()

    def authenticate(self, client_id, client_secret, redirect_url):
        #coinbase_oauth = coinbase.CoinbaseOAuth(client_id, client_secret, redirect_url)
        
        #1. If no auth.json file:
        #print(coinbase_oauth.create_authorize_url(scopes))

        #a. Waiting for user input : code
        #tokens = coinbase_oauth.get_tokens(code)
        
        #b. save tokens to auth file 

        #2. if auth.json file:
        # load access and refresh token
        # try receiving something
        # if token expired, get new token from refresh_token:
        #tokens = coinbase_oauth.get_tokens(refresh_token, grant_type='refresh_token')
        # save tokens to file
        # return self.autehnticate(...) ---> call again

        # return coinbase.Coinbase.with_oauth(atoken, rtoken)

        return NotImplemented

    def getAllAccounts(self):
        self.accounts += self.__getPaginatedResult('/accounts')

    def getBalance(self) -> dict:
        balance = dict()
        for account in self.accounts:
            if Decimal(account["balance"]["amount"]) == 0:
                continue
            balance[account["balance"]["currency"]] = Decimal(account["balance"]["amount"])
        return balance

    def __getPaginatedResult(self, getUrl:str) -> list:
        elems = []
        data = self.client.get(getUrl)
        elems += data["data"]
        while data["pagination"]["next_starting_after"] != None:
            data = self.client.get(getUrl, params={'starting_after': data["pagination"]["next_starting_after"]})
            elems += data["data"]
            sleep(0.006)
        return elems
    
    def _getRawTransactionsPerAccount(self, accountId:str) -> list:
        rawTxs = self.__getPaginatedResult('/accounts/{}/transactions'.format(accountId))
        return rawTxs

    def _getRawTransactions(self) -> None:
        for account in self.accounts:
            self.rawTxs += self._getRawTransactionsPerAccount(account["id"])

    def _handleFiatDeposit(self, txRaw) -> Transaction:
        t = Transaction(dateTime=txRaw["created_at"], posIn=Position( Decimal(txRaw["amount"]["amount"]),  txRaw["amount"]["currency"]) )
        t.note += txRaw["details"]["title"] + '. ' + txRaw["details"]["subtitle"]
        return t

    def _handleFiatWithdrawal(self, txRaw) -> Transaction:
        #print(txRaw)
        t = Transaction(dateTime=txRaw["created_at"], posOut=Position( abs(Decimal(txRaw["amount"]["amount"])),  txRaw["amount"]["currency"]) )
        t.note += txRaw["details"]["title"] + '. ' + txRaw["details"]["subtitle"]
        return t

    def _handleExchangeDeposit(self, txRaw) -> Transaction:
        t = Transaction(dateTime=txRaw["created_at"], posOut=Position( abs(Decimal(txRaw["amount"]["amount"])),  txRaw["amount"]["currency"]) )
        t.note += txRaw["details"]["title"] + '. ' + txRaw["details"]["subtitle"]
        return t
    
    def _handleExchangeWithdrawal(self, txRaw) -> Transaction:
        """From Coinbase Pro to Coinbase """
        t = Transaction(dateTime=txRaw["created_at"], posIn=Position( abs(Decimal(txRaw["amount"]["amount"])),  txRaw["amount"]["currency"]) )
        t.note += txRaw["details"]["title"] + '. ' + txRaw["details"]["subtitle"]
        return t

    def _handleBuy(self, txRaw) -> Transaction:
        if txRaw["details"]["payment_method_name"].lower().find("wallet") != -1:
            #match found
            buyWithoutInternalWallet = False
        else:
            buyWithoutInternalWallet = True

        buy = self.client.get(txRaw["buy"]["resource_path"].replace('/v2',''))["data"]
        if buy["status"] != "completed":
            print("BUY: STATUS NOT COMPLETED {}".format(txRaw["sell"]["resource_path"]))
            return Transaction()
        #print(buy)
        t = Transaction(dateTime=txRaw["created_at"])
        t.orderId = txRaw["id"]
        t.posIn = Position( Decimal(buy["amount"]["amount"]),  buy["amount"]["currency"])
        t.posOut = Position( Decimal(buy["subtotal"]["amount"]), buy["subtotal"]["currency"])
        t.fee = Fee( Decimal(buy["fee"]["amount"]), buy["fee"]["currency"])
        t.tradeId = buy["transaction"]["id"]

        #we create a new deposit in case we have a buy without using the internal wallets
        if buyWithoutInternalWallet:
            t2 = Transaction(dateTime=txRaw["created_at"])
            t2.posIn = Position( Decimal(buy["total"]["amount"]), buy["total"]["currency"])
            t2.note = "Deposit for buy with payment method {}".format(txRaw["details"]["payment_method_name"])
            t2.orderId = "deposit/"+txRaw["id"]
            if self.txList.fromOrderId(t2.orderId) is None:
                self.txList.append(t2) #we can just add it here, because there won't be another transaction with the same id

        #t.note += txRaw["details"]["title"] + '. ' + txRaw["details"]["subtitle"]
        return t

    def _handleSell(self, txRaw) -> Transaction:
        sell = self.client.get(txRaw["sell"]["resource_path"].replace('/v2',''))["data"]
        if sell["status"] != "completed":
            print("SELL: STATUS NOT COMPLETED {}".format(txRaw["sell"]["resource_path"]))
            return Transaction()
        #print(buy)
        t = Transaction(dateTime=txRaw["created_at"])
        t.orderId = txRaw["id"]
        t.posOut = Position( Decimal(sell["amount"]["amount"]), sell["amount"]["currency"])
        t.posIn = Position( Decimal(sell["subtotal"]["amount"]), sell["subtotal"]["currency"])
        t.fee = Fee( Decimal(sell["fee"]["amount"]), sell["fee"]["currency"])
        t.tradeId = sell["transaction"]["id"]
        #t.note += txRaw["details"]["title"] + '. ' + txRaw["details"]["subtitle"]
        return t

    def _handleTrade(self, txRaw) -> Transaction:

        """The trade endpoint seems not to work
        trade = self.client.get(txRaw["trade"]["resource_path"].replace('/v2',''))["data"]
        if trade["status"] != "completed":
            print("TRADE: STATUS NOT COMPLETED {}".format(txRaw["sell"]["resource_path"]))
            return Transaction()
        """
        tradeId = txRaw["trade"]["id"]
        if self._trades.fromOrderId(tradeId):
            tmp,idx = self._trades.fromOrderId(tradeId)
        else:
            tmp = Transaction(dateTime=txRaw["created_at"])
            tmp.orderId = tradeId
            self._trades.append(tmp)
        
        t,idx = self._trades.fromOrderId(tradeId)
        amount =  Position( Decimal(txRaw["amount"]["amount"]), txRaw["amount"]["currency"])
        if amount.amount > 0:
            t.posIn = Position( amount.amount, amount.currency)
        elif amount.amount < 0:
            t.posOut = Position( abs(amount.amount), amount.currency)
        
        if "fee" in txRaw:
            t.fee = Fee( Decimal(txRaw["fee"]["amount"]), txRaw["fee"]["currency"])
        
        #self._trades.append(t)
        
        #t.note += txRaw["details"]["title"] + '. ' + txRaw["details"]["subtitle"]
        return t
    
    def _handleSend(self, txRaw) -> Transaction:
        """ E.g. Coinbase Earn """
        if txRaw["status"] != "completed":
            print("SEND: STATUS NOT COMPLETED {}".format(txRaw["sell"]["resource_path"]))
            return Transaction()

        t = Transaction(dateTime=txRaw["created_at"])
        amount = Decimal( txRaw["amount"]["amount"] )
        currency = txRaw["amount"]["currency"] 
        if amount > 0:
            t.posIn = Position( amount, currency)
        else:
            t.posOut = Position( abs(amount), currency)
        
        if "fee" in txRaw:
            t.fee = Fee( Decimal(txRaw["fee"]["amount"]), txRaw["fee"]["currency"])
        
        if "to" in txRaw:
            if "address" in txRaw["to"] and amount <0:
                t.toAddress = txRaw["to"]["address"]
        
        # Overwrite with network values if availabe and if they are different
        if "network" in txRaw:
            if "hash" in txRaw["network"]:
                t.txHash = txRaw["network"]["hash"]
            if "transaction_amount" in txRaw["network"]:
                amount2 = Decimal( txRaw["network"]["transaction_amount"]["amount"] )
                currency2 = txRaw["network"]["transaction_amount"]["currency"]
                if amount2 != abs(amount) and amount2 != 0:
                    if amount > 0: #amount2 is always positive
                        t.posIn = Position( amount2, currency2)
                    else:
                        t.posOut = Position( abs(amount2), currency2)
            if "transaction_fee" in txRaw["network"] and Decimal( txRaw["network"]["transaction_fee"]["amount"] ) != t.fee.amount:
                t.fee = Fee( Decimal( txRaw["network"]["transaction_fee"]["amount"] ), txRaw["network"]["transaction_fee"]["currency"] )

        t.orderId = txRaw["id"]
        t.price = Position( abs( Decimal( txRaw["native_amount"]["amount"] ) ), txRaw["native_amount"]["currency"] )
        t.note += txRaw["details"]["title"] + '. ' + txRaw["details"]["subtitle"]
        return t


    def _handleRawTx(self, txElem) -> Transaction:
        tx = Transaction()
        if txElem["type"] == "exchange_deposit":
            tx = self._handleExchangeDeposit(txElem)

        elif txElem["type"] == "exchange_withdrawal" or txElem["type"] == "pro_withdrawal":
            tx = self._handleExchangeWithdrawal(txElem)

        elif txElem["type"] == "fiat_deposit":
            tx = self._handleFiatDeposit(txElem)

        elif txElem["type"] == "fiat_withdrawal":
            tx = self._handleFiatWithdrawal(txElem)

        elif txElem["type"] == "buy":
            tx =  self._handleBuy(txElem)

        elif txElem["type"] == "sell":
            tx = self._handleSell(txElem)
        
        elif txElem["type"] == "send":
            tx = self._handleSend(txElem)

        elif txElem["type"] == "trade": #not documented in API
            tx = self._handleTrade(txElem)
        
        # Todo: Implement:
        elif txElem["type"] == "transfer":
            print("transfer")
            pass 

        elif txElem["type"] == "request":
            print("request")
            pass 
        elif txElem["type"] == "vault_withdrawal":
            print("vault")
            pass
        elif txElem["type"] == "advanced_trade_fill":
            print("advanced")
            pass

        else:
            print("UNKNOWN:")
            print(txElem)
        
        return tx
    
    def getTransactions(self, time=None) -> TransactionList:
        self.getAllAccounts()
        print("Fetched all accounts")
        sleep(0.006)
        print("Getting all txs")
        self._getRawTransactions()
        print("Done")
        sleep(0.006)

        for tx in self.rawTxs:
            if self.txList.fromOrderId(tx["id"]) is not None:
                continue
            if tx["type"] == "trade":
                #trades are a bit buggy, so we handle them in a different list
                self._handleRawTx(tx)
            else:
                tmp = self._handleRawTx(tx)
                if tmp.tradeId != '' and self.txList.fromTradeId(tmp.tradeId) is not None:
                    continue
                else:
                    self.txList.append( self._handleRawTx(tx) )

        self.txList += self._trades
        
        self.txList.sort(key=lambda r: r.datetime)

        return self.txList



        #TODO: check payment method ---> credit card should create a new deposit entry