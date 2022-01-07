from abc import abstractclassmethod, abstractmethod


import abc
from pyCryptoTransactions.Transaction import TransactionList,Transaction
#import Transaction, TransactionList

class Importer(metaclass=abc.ABCMeta):

    Network = None

    def __init__(self):
        self.txList = TransactionList()

    #@property
    #def BLOCK_EXPLORER_URL(self):
    #    return self._blockExplorerUrl

    @abc.abstractmethod
    def getTransactions(self, time=None) -> TransactionList:
        pass