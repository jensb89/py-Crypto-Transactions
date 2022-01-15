from abc import abstractclassmethod, abstractmethod
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
from requests import Request, Session
import json
import time

import abc
from pyCryptoTransactions.Transaction import TransactionList,Transaction
#import Transaction, TransactionList

class Importer(metaclass=abc.ABCMeta):

    Network = None

    def __init__(self):
        self.txList = TransactionList()
        self._apiAdress = ""

    #@property
    #def BLOCK_EXPLORER_URL(self):
    #    return self._blockExplorerUrl

    @abc.abstractmethod
    def getTransactions(self, time=None) -> TransactionList:
        pass

    ########## HELPER FUNCTION ######################

    def _returnValueFromPath(self, dictElement, path):
        mydata = dictElement
        for i in path:
            mydata = mydata[i]
        return mydata
    
    def _initRequest(self):
        headers = {'Accepts': 'application/json'}
        self.session = Session()
        self.session.headers.update(headers)
    
    def _request(self, path, apiAdress = None, **params):
        if apiAdress == None:
            apiAdress = self._apiAdress
        try:
            #print(params)
            response = self.session.get(apiAdress + path, params=params)
            #print(response.url)
            if response.status_code != 200:
                raise("Error in the request")

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
                time.sleep(1)
                return data
            else:
                print("No data in request") #raise("Data failure")
        except (ConnectionError, Timeout, TooManyRedirects) as e:
            print(e)
            raise("Connection Error")