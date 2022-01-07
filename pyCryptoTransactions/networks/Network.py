from abc import abstractclassmethod, abstractmethod


import abc
#import Transaction, TransactionList

class Network(metaclass=abc.ABCMeta):

    def __init__(self, blockExplorerUrl):
        self._blockExplorerUrl = blockExplorerUrl

    @property
    def BLOCK_EXPLORER_URL(self):
        return self._blockExplorerUrl

    @abc.abstractmethod
    def getTransactions(self, address, time=None): #-> "TransactionList":
        return