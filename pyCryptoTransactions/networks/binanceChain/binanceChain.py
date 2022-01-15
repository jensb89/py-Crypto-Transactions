from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
from datetime import datetime
import time
#from django.utils import timezone
import pytz as timezone
from decimal import Decimal
from copy import deepcopy

from pyCryptoTransactions.Transaction import Position, Transaction,TransactionList, Fee
from pyCryptoTransactions.Importer import Importer

class BinanceChain(Importer):
    def __init__(self, address):
        super().__init__()
        self._apiAdress = 'https://dex.binance.org/api/v1'
        self._initRequest()
        self.rawTxs = None
        self.address = address
        self.denominator = Decimal(int(1E8))
        self.cancelledOrders = list()
    
    def _initRequest(self):
        headers = {'Accepts': 'application/json'}
        self.session = Session()
        self.session.headers.update(headers)
    
    def _request(self, path, **params):
        try:
            #print(params)
            response = self.session.get(self._apiAdress + path, params=params)
            #print(response.url)
            data = json.loads(response.text)
            if "ok" in data:
                if not(data["ok"]):
                    print(data)
                    raise("Error in the Request")
            if "code" in data:
                if data["code"] != 0:
                    print(data)
                    raise("Error in the request")
            if data: #data['ok'] and data["code"]==0:
                return data
            else:
                raise("Data failure:" + data['log'])
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            print(e)
            raise("Connection Error")
    
    # Endpoint doesn't give multisend transactions!
    def _getRawTransactions(self, offset=0, limit=500, **kwargs):#offset=0, limit=500, startTime=None, endTime = int(round(time.time() * 1000))):
        values = {}
        values['address'] = self.address
        values['offset'] = offset
        values['limit'] = limit
        for k in kwargs:
            if kwargs[k] is not None:
                values[k] = kwargs[k]
        self._request('/transactions', **values)

    def getTransaction(self, txId):
        """ Get a transaction for a given tx ID """
        #https://docs.binance.org/api-reference/dex-api/paths.html#apiv1transactions
        args = {}
        args['format'] = 'json'
        return self._request('/tx/' + txId, **args)
    
    def getOrder(self, orderId):
        args = {}
        args["format"] = 'json'
        return self._request('/orders/' + orderId, **args)
    
    def getTrades(self, orderId, timestamp:int, isBuy:bool):
        args = {}
        args["format"] = 'json'
        args["start"] = timestamp -10
        args["end"] = timestamp + 10
        if isBuy:
            args["buyerOrderId"] = orderId
        else:
            args["sellerOrderId"] = orderId
        print(args)
        return self._request('/trades', **args)

    def getFees(self):
        return self._request('/fees')

    #def getTrades(self,offset=0, limit=500, **kwargs):
    #    values = {}
    #    values['offset'] = offset
    #    values['limit'] = limit
    #    for k in kwargs:
    #        if kwargs[k] is not None:
    #            values[k] = kwargs[k]
    #    self._request('/trades', **values)


    def getTransactionsPage(self,page=-1):
        """get Raw Tx Data for the given address from the binance explorer. 
           Note: page must be negative!
        """
        # Get a page also inlcuding multisend transactions
        #https: // github.com / binance - chain / java - sdk / issues / 30
        #https://explorer.binance.org/api/v1/txs?page=-1&rows=100&address=ADDRESS
        params = {'address':self.address, 'page':page, 'rows':100}
        tmpApiAddress = self._apiAdress
        self._apiAdress = "https://explorer.binance.org/api/v1"
        ret = self._request('/txs', **params)
        self._apiAdress = tmpApiAddress
        return ret

    def _getAllRawTxsFromTxPage(self):
        # Query first page
        page = -1
        dataTransactionPage = self.getTransactionsPage(page=page)
        numTxs = dataTransactionPage["txNums"]
        numTxsQueried = 100
        while numTxsQueried < numTxs:
            page -= 1
            tmp = self.getTransactionsPage(page=page)
            numTxsQueried += 100
            print(type(tmp))
            dataTransactionPage.update(tmp)
            #d.update(tmp)
            #dataTransactionPage += dict(dataTransactionPage.items() | tmp.items())
        self.rawTxs = dataTransactionPage
        #todo: remove all txs over a given minimum time

    # currently unused
    def _getAllMultiSendTransactionIds(self):
        multiSendTxIds = []
        for entry in self.rawTxs:
            if entry["hasChildren"] > 0:
                multiSendTxIds.append(entry["txHash"])

        return multiSendTxIds

    def _getAllTransactionIds(self):
        ids = []
        for entry in self.rawTxs["txArray"]:
            ids.append((entry["timeStamp"],entry["txHash"],entry["txFee"]))
        return ids
    
    #def manualImportTransactionFromID(self, txID):
    #    tx = self.getTransaction(txID)
    #    t = Transaction()
    #    t.txHash = result["hash"]
    #    t.datetime = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)

    def getTransactions(self, startTime=None, offset=None) -> 'TransactionList':
        self._getAllRawTxsFromTxPage()
        for timestamp, id, feeValue in self._getAllTransactionIds():
            feeValue = Decimal(str(feeValue))
            result = self.getTransaction(id)

            t = Transaction(network="binanceChain")

            #only transactions of type "auth/StdTx" are supported
            if result["tx"]["type"] != "auth/StdTx":
                print("Unsupported transaction with id {}".format(id))
                continue

            t.txHash = result["hash"]
            t.datetime = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)

            #print(result["tx"]["value"]["msg"])
            # Only take first one, typically there are no more , TODO: Check or do better :)
            if result["tx"]["value"]["msg"][0]["type"] == "cosmos-sdk/Send":
                transaction = result["tx"]["value"]["msg"][0]["value"]

                isMulitSend = self.isMultiSendTransaction(result)
                isOutTransaction = self.isOutTransaction(result)

                if isOutTransaction:
                    t.category = "Transfer Out" if not(isMulitSend) else "Stake"
                    if feeValue>0:
                        t.fee = Fee(feeValue,"BNB")
                    else:
                        t.fee = Fee(Decimal(37500)/self.denominator if not(isMulitSend) else Decimal(30000)/self.denominator, "BNB")
                    coins = transaction["outputs"][0]["coins"]
                    #fixedFees = self.getFees()["fixed_fee_params"]  # Todo query fixed fees
                else:
                    t.category = "Transfer In" if not (isMulitSend) else "Harvest"
                    coins = transaction["inputs"][0]["coins"]

                if not(isMulitSend) and result["tx"]["value"]["memo"].find("SWAP") != -1 or result["tx"]["value"]["memo"].find("OUTBOUND") != -1:
                    t.category = "Swap"

                if result["tx"]["value"]["memo"]:
                    t.note = "memo:" + result["tx"]["value"]["memo"]

                i = 0
                for coin in coins:
                    tmp = deepcopy(t)
                    if isOutTransaction:
                        tmp.posOut = Position(Decimal(coin["amount"])/self.denominator, coin["denom"].split("-")[0])
                    else:
                        tmp.posIn = Position(Decimal(coin["amount"])/self.denominator, coin["denom"].split("-")[0]) 
                    if i>0:
                        tmp.fee.amount = Decimal(0)
                    self.txList.append(tmp)
                    i+=1
                    # Hack: Put equivalent transaction for BEPSWAP
                    #if tmp["category"] == "Stake":
                    #    tmp2 = tmp.copy()
                    #    tmp2["amountIn"] = tmp2["amountOut"]
                    #    tmp2["currencyIn"] = tmp2["currencyOut"]
                    #    tmp2["amountOut"] = 0
                    #    tmp2["category"] = "LP"
                    #    tmp2["wallet"] = "Bepswap"
                    #    transactios.append(tmp2)

            elif result["tx"]["value"]["msg"][0]["type"] == "dex/NewOrder": #BUY
                t.note = "dex/New Order"
                t.category = "Trade"
                order = result["tx"]["value"]["msg"][0]["value"]
                t.orderId = order["id"]
                orderInfo = self.getOrder(t.orderId)
                pair = order["symbol"].split('_')

                trades = self.getTrades(timestamp=int(t.datetime.timestamp()*1E3), orderId=t.orderId, isBuy=orderInfo["side"]==1)
                if order["ordertype"] == 2 and order["side"]==2: #sell
                    posIn = Position(Decimal(0),pair[1].split('-')[0])
                    posOut = Position(Decimal(0),pair[0].split('-')[0])
                    fee = Fee(0, "BNB")
                    for trade in trades["trade"]:
                        posIn += Position( Decimal(trade["price"].rstrip("0")) * Decimal(trade["quantity"].rstrip("0")), pair[1].split('-')[0])
                        posOut += Position( Decimal(trade["quantity"].rstrip("0")), pair[0].split('-')[0])
                    fee = Fee( Decimal(trade["sellFee"].split(";")[0].split("BNB:")[1]), "BNB")
                elif order["ordertype"] == 2 and order["side"]==1: #buy
                    posIn = Position(Decimal(0),pair[0].split('-')[0])
                    posOut = Position(Decimal(0),pair[1].split('-')[0])
                    for trade in trades["trade"]:
                        posIn += Position(  Decimal(trade["quantity"].rstrip("0")), pair[0].split('-')[0])
                        posOut += Position(Decimal(trade["price"].rstrip("0")) * Decimal(trade["quantity"].rstrip("0")), pair[1].split('-')[0])
                    fee = Fee( Decimal(trade["buyFee"].split(";")[0].split("BNB:")[1]), "BNB")

                t.posIn = posIn
                t.posOut = posOut
                t.fee = fee
                    
                #orderPrice1 = Decimal(order["price"])/self.denominator
                #orderQuantity1 = Decimal(order["quantity"])/self.denominator

               #print("{} == P1:{} Q1:{}, P2:{}, Q2:{} ({})".format(t.orderId, orderPrice1,orderQuantity1,orderPrice,orderQuantity,pair))

                if t.orderId in self.cancelledOrders or orderInfo["status"]=="Canceled":
                    continue
                #if order["ordertype"] == 2 and order["side"]==2: #sell
                #    t.posIn = Position(orderPrice * orderQuantity, pair[1].split('-')[0])
                #    t.posOut = Position(orderQuantity, pair[0].split('-')[0])
                #elif order["ordertype"] == 2 and order["side"]==1: #buy
                #    t.posIn = Position(orderQuantity, pair[0].split('-')[0])
                #    t.posOut = Position(orderPrice * orderQuantity, pair[1].split('-')[0])
                
                #t.fee = Fee(0, "BNB")
                t.price = Decimal(order["price"])/self.denominator
                t.tradingPair = (pair[0].split('-')[0], pair[1].split('-')[0])
                
                self.txList.append(t)

            elif result["tx"]["value"]["msg"][0]["type"] == "bridge/TransferOutMsg":
                # Swap to bsc network chain
                t.note = "Atomic Swap to BSC Chain"
                t.category = "Swap"
                t.posOut = Position(Decimal(result["tx"]["value"]["msg"][0]["value"]["amount"]["amount"]) / self.denominator, result["tx"]["value"]["msg"][0]["value"]["amount"]["denom"].split('-')[0])
                t.fee = Fee(Decimal("0.0002"), "BNB")
                self.txList.append(t)
            elif result["tx"]["value"]["msg"][0]["type"] == "dex/CancelOrder":
                # we must find orders that match this order id or prevent new ones getting added
                order = result["tx"]["value"]["msg"][0]["value"]
                orderId = order["refid"]
                if self.txList.fromOrderId(orderId) is not None:
                    self.txList.remove(self.txList.fromOrderId(orderId))
                else:
                    self.cancelledOrders.append(orderId)
                t.category = "Loss"
                t.fee = Fee(Decimal("0.00001"),"BNB")
                self.txList.append(t)
            else:
                raise("Unknown type: %s" % result["tx"]["value"]["msg"][0]["type"])

        return self.txList

    def isMultiSendTransaction(self, txResult):
        value = txResult["tx"]["value"]["msg"][0]["value"]
        if "inputs" in value and len(value["inputs"][0]["coins"]) > 1:
            return True
        if "outputs" in "value" and len(value["outputs"][0]["coins"]) > 1:
            return True
        return False

    def isOutTransaction(self, txResult):
        value = txResult["tx"]["value"]["msg"][0]["value"]
        if "inputs" in value and value["inputs"][0]["address"] == self.address:
            return True
        elif "outputs" in value and value["outputs"][0]["address"] == self.address:
            return False
        else:
            raise("Error: Input address not found in transacion entry!")

    #def get(self, address):
    #    # try to grab it all
    #    trades = self.getTrades()
    #    transactions = self._getRawTransactions(address=address, startTime=1609894800000, endTime=int(round(time.time() * 1000)))
    #    multiSendTransactions = []
    #    multiSendTransactionIds = self._getAllMultiSendTransactionIds(address=address)
    #    for id in multiSendTransactions:
    #        multiSendTransactions.append(self.getTransaction(id))

        # Now put it all together:
        # tbd





