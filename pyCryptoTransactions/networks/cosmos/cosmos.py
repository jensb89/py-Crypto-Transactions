from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
from datetime import datetime

import pytz as timezone
from decimal import Decimal
from copy import deepcopy

from pyCryptoTransactions.Transaction import Position, Transaction,TransactionList, Fee
from pyCryptoTransactions.Importer import Importer
import time

class CosmosChain(Importer):
    def __init__(self, address):
        super().__init__()
        self._apiAdress = 'https://api.cosmostation.io/v1/'
        self._initRequest()
        self.rawTxs = None
        self.address = address
        self.ibcTokens = None
        self.denominator = Decimal(int(1E6))
        self.chain = "cosmoshub-4"
        self.ibcTokenApiAddress = "https://api-utility.cosmostation.io/v1//ibc/tokens/cosmoshub-4"
        self.unit = "ATOM"

        self._getAllIBCTokens()
    
    @property
    def pathToMemo(self):
        pathOld = ["data","tx","value","memo"]
        pathNew = ["data","tx","body","memo"]
        return pathOld if self.chain == "cosmoshub-3" else pathNew
    
    @property
    def pathToFee(self):
        pathOld = ["data","tx","value","fee","amount",0,"amount"]
        pathNew = ["data","tx","auth_info","fee","amount",0,"amount"]
        return pathOld if self.chain == "cosmoshub-3" else pathNew
    
    @property
    def pathToFeeCurrency(self):
        pathOld = ["data","tx","value","fee","amount",0,"denom"]
        pathNew = ["data","tx","auth_info","fee","amount",0,"denom"]
        return pathOld if self.chain == "cosmoshub-3" else pathNew
    
    # Endpoint doesn't give multisend transactions!
    def _getRawTransactions(self, offset=0, limit=50, **kwargs):#offset=0, limit=500, startTime=None, endTime = int(round(time.time() * 1000))):
        values = {}
        values['limit'] = limit
        values['from'] = offset
        for k in kwargs:
            if kwargs[k] is not None:
                values[k] = kwargs[k]
        return self._request('/account/new_txs/{}'.format(self.address), **values)
    
    def _getAllIBCTokens(self):
        data= self._request('',apiAdress=self.ibcTokenApiAddress)
        self.ibcTokens = data
        print("Fetched {} IBC Tokens".format(len(self.ibcTokens["ibc_tokens"])))
    
    def getIbcTokenSymbolFromIBCTokenHash(self, ibcTokenHash):
        symbol = "ibc/"+ibcTokenHash
        decimal = self.denominator
        for token in self.ibcTokens["ibc_tokens"]:
            if token["hash"] == ibcTokenHash.strip():
                if "decimal" in token:
                    decimal = '1' + int(token["decimal"])*'0'
                if "display_denom" in token:
                    symbol = token["display_denom"]
                elif "base_denom" in token:
                    symbol = token["base_denom"]
                return symbol, decimal
        print("Could not find token name for IBC token {}".format(ibcTokenHash))
        return symbol,decimal
    
    def getSymbol(self, symbol):
        if symbol == "uatom":
            return "ATOM"
        if symbol == "uosmo":
            return "OSMO"
        if symbol == "uion":
            return "ION"
        if symbol == "uxprt":
            return "XPRT"
        return symbol
    
    def _getAllRawTransactions(self):
        offset = 0
        rawData = self._getRawTransactions(offset=offset, limit=50)
        numTxs = len(rawData)
        while numTxs == 50:
            print("Fetching another page starting from block id {}".format(rawData[-1]["header"]["block_id"]))
            lastBlock = rawData[-1]["header"]["block_id"]
            tmp = self._getRawTransactions(offset=lastBlock, limit=50)
            numTxs = len(tmp)
            if tmp:
                rawData.extend(tmp) #todo:check
        return rawData
    
    def _parseAmount(self, amountStr) -> str:
        """Parse amount values like 1234uatom"""
        if amountStr.isdigit():
            #no unit
            number = amountStr
            unit = self.unit 
        else:
            for i,c in enumerate(amountStr):
                if not c.isdigit():
                    break
            number = amountStr[:i]
            unit = amountStr[i:].lstrip()
        return number, unit

    def _parseAmounts(self, amountStr) -> list:
        amounts = amountStr.split(',')
        amountList = list()
        for amount in amounts:
            number, unit = self._parseAmount(amount)
            if unit == '' and float(number) > 0:
                unit = self.unit
            # check for ibc token
            if unit[0:4] == "ibc/":
                unit, decimal = self.getIbcTokenSymbolFromIBCTokenHash(unit[4:])
            else:
                unit = self.getSymbol(unit)
                decimal = self.denominator
            
            amountList.append(Position(Decimal(number)/Decimal(decimal), unit))
        return amountList

    def _findEventByType(self, allEvents, type:str):
        for event in allEvents:
            if event["type"] == type:
                return event
        return None
    
    def handleEvents(self, events, currentTransactionObject):
        txList = self.handleTransferEvent(events, currentTransactionObject)
        isDelegated, delegatedAmount = self.handleDelegationEvent(events)
        hasReward, rewards = self.handleRewardEvent(events)
        hasProposal = self.handlePropsoalEvent(events)
        hasClaim, claims = self.handleClaimEvent(events) #more for osmosis then for cosmos

        # If we have a delegation event and a tx input/output(?) then we have a auto claim reward
        if txList and isDelegated:
            for tx in txList:
                tx.note += "Delegated {}{}".format(delegatedAmount.amount, delegatedAmount.currency) + " (+auto claim reward)"
                tx.category = "Staking"

        # If we have no input and ouput txs but a delegated event, we only have transaction fees -> we create a new txlist with one entry
        if not txList and isDelegated:
            txList = TransactionList()
            currentTransactionObject.note = "Delegated {}{}".format(delegatedAmount.amount, delegatedAmount.currency)
            txList.append(currentTransactionObject)
        
        # If Rewards are included, find the transaction with the reward and mark it as "Staking"
        if hasReward:
            for tx in txList:
                for reward in rewards:
                    if tx.posIn == reward:
                        tx.category = "Staking"
                        tx.note += "Staking Reward"
        
        if hasClaim:
            for tx in txList:
                for claim in claims:
                    if tx.posIn == claim:
                        tx.category = "Staking"
                        tx.note += "Airdrop (?)"


        #Remove fees for received txs only:
        for tx in txList:
            if (tx.posIn.amount != 0 and not(isDelegated) and not(hasReward) and not (hasProposal) and not(hasClaim)): #when it has a reward we must have sent a tx fee
                tx.fee.amount = 0
        
        return txList

    def handleDelegationEvent(self, events):
        isDelegated = False
        delegatedAmount = Position(0,"")
        event = self._findEventByType(events,"delegate")
        if event != None:
            isDelegated = True 
            for attr in event["attributes"]:
                if attr["key"] == "amount":
                    delegatedAmounts = self._parseAmounts(attr["value"])
                    assert(len(delegatedAmounts) == 1) #there should only be one delegation at a time
                    delegatedAmount = delegatedAmounts[0]
        return isDelegated, delegatedAmount
    
    def handleRewardEvent(self, events):
        event = self._findEventByType(events,"withdraw_rewards")
        rewards = list()
        if event:
            for attr in event["attributes"]:
                if attr["key"] == "amount":
                    rewards = self._parseAmounts(attr["value"])
            return True, rewards
        else:
            return False, rewards

    def handlePropsoalEvent(self, events):
        event = self._findEventByType(events, "proposal_vote")
        if event:
            return True 
        else:
            return False
    
    def handleClaimEvent(self, events):
        event = self._findEventByType(events, "claim")
        claims = list()
        if event:
            for attr in event["attributes"]:
                if attr["key"] == "amount":
                    claims = self._parseAmounts(attr["value"])
            return True, claims
        else:
            return False, claims

    def handleTransferEvent(self, events, currentTransactionObject) -> TransactionList:
        event = self._findEventByType(events,"transfer")
        if event == None:
            return TransactionList()

        transferAttributes = event["attributes"]
        numAttributes = len(transferAttributes)
        txList = TransactionList()
        start = 0
        while(start+1 < numAttributes):
            tmp = deepcopy(currentTransactionObject)
            # Find sender and recipient
            recipientIdx = None
            senderIdx = None
            amountIdx = None
            for idx,attr in enumerate(transferAttributes[start:]):
                if attr["key"] == "recipient":
                    recipientIdx = idx + start
                if attr["key"] == "sender":
                    senderIdx = idx + start
                if attr["key"] == "amount":
                    amountIdx = idx + start
                    # We need at least a sender or recipient and an amount
                    assert(recipientIdx!=None or senderIdx!=None)
                    assert(amountIdx!=None)
                    assert(amountIdx > 0)
                    # We stop here as we have found one set, amount should always be the last one
                    start = start + idx + 1
                    break
            
            # Fill to and from address
            if recipientIdx is not None:
                tmp.toAddress = transferAttributes[recipientIdx]["value"]
            if senderIdx is not None:
                tmp.fromAddress = transferAttributes[senderIdx]["value"]
            
            # Parse amounts
            amountPositions = self._parseAmounts(transferAttributes[amountIdx]["value"])
            for amount in amountPositions:
                tmp2 = deepcopy(tmp)
                #check for in or out transaction
                if tmp2.fromAddress == self.address:
                    tmp2.posOut = amount
                    txList.append(tmp2)
                elif tmp2.toAddress == self.address:
                    tmp2.posIn = amount
                    txList.append(tmp2)
                
        # Finally declutter the list (find and remove opposite transactions)
        for txElem in txList:
            for txElem2 in txList:
                if (txElem.posIn == txElem2.posOut and txElem.posIn.amount != 0) or (txElem.posOut == txElem2.posIn and txElem.posOut.amount != 0): #and txElem.fromaddress == txElem2.toAddress:
                    #print("REMOVING in tx hash {} where posIn1 ={}, posOut2={}, posOut1={}, posIn2={}".format(txElem.txHash, txElem.posIn.amount, txElem2.posOut.amount, txElem.posOut.amount, txElem2.posIn.amount))
                    txList.remove(txElem)
                    txList.remove(txElem2)
        
        # Find trades
        for txElem in txList:
            for txElem2 in txList:
                if txElem.fromAddress == txElem2.toAddress and txElem.toAddress == txElem2.fromAddress:
                    txElem.combinePositions(txElem2)
                    txElem.category = "Swap"
                    txList.remove(txElem2)
        if len(txList) == 2 and (txList[0].posIn.amount == 0 or txList[0].posOut.amount == 0) and (txList[1].posIn.amount == 0 or txList[1].posOut.amount == 0):
            txList[0].combinePositions(txList[1])
            txElem.category = "Swap"
            txList.remove(txElem2)
            
        return txList


    def getTransactions(self, time=None) -> TransactionList:
        self.rawTxs = self._getAllRawTransactions()

        for tx in self.rawTxs:
            self.chain = tx["header"]["chain_id"]
            time = datetime.strptime(tx["header"]["timestamp"],"%Y-%m-%dT%H:%M:%SZ")
            height = tx["data"]["height"]
            txHash = tx["data"]["txhash"]

            t = Transaction(dateTime=time, txHash=txHash, blockHeight=height)
            #print(txHash)
            #1. Fee
            try:
                fee = self._returnValueFromPath(tx, self.pathToFee)
                feeCurrency = self._returnValueFromPath(tx, self.pathToFeeCurrency)
                t.fee = Fee(Decimal(fee)/self.denominator, self.getSymbol(feeCurrency) )
            except IndexError:
                print("No fee found for transaction {}".format(txHash))

            #2.Memo
            t.memo = self._returnValueFromPath(tx, self.pathToMemo)

            #3. Check for failed transaction
            if not("logs" in tx["data"]):
                t.category = "Loss"
                if t.fee.amount > 0:
                    self.txList.append(t)
                continue 

            #4. Loop all logs and events
            txs = TransactionList()
            for log in tx["data"]["logs"]:
                tmp = deepcopy(t)
                events = log["events"] #todo: check --> no logs for failed txs
                txs += self.handleEvents(events, tmp)

            # Remove doubled fees, fee is only added per transaction and not per log or per event
            feeAdded = False
            for tx in txs:
                if tx.fee.amount > 0 and not(feeAdded):
                    feeAdded = True
                elif tx.fee.amount > 0 and feeAdded:
                    tx.fee.amount = 0

            self.txList.extend(txs)
        return self.txList