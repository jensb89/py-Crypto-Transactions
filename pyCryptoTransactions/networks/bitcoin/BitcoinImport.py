from pycoin.symbols.btc import network as BTC
from pycoin.convention import satoshi_to_btc
import requests
import time
import blockcypher
from enum import Enum

from pyCryptoTransactions.networks.Network import Network
from pyCryptoTransactions.Transaction import Position, Transaction, TransactionList, Fee
from pyCryptoTransactions.Importer import Importer

class AddresType(Enum):
    LEGACY = 0
    SEGWIT = 1
    NATIVE_SEGWIT = 2
    

class BitcoinImport(Importer):
    Network = BTC

    def __init__(self, publicKey):
        '''
        The __init__ function is called when an instance of the class is created
        :param publicKey: The public key of the user
        '''
        super().__init__()
        self.publicKey = publicKey
        self._blockExplorerUrl = "http://blockchain.info"
    
    def _getSubkey(self, receiveAddr:bool=True, changeAddr:bool=False, number=0):
        '''
        It takes the public key and the desired subkey path as arguments and returns the subkey
        
        :param receiveAddr: True if you want to receive coins, False if you want to change coins, defaults
        to True
        :type receiveAddr: bool (optional)
        :param changeAddr: If True, return the change address for the account. If False, return the
        receiving address, defaults to False
        :type changeAddr: bool (optional)
        :param number: the index of the subkey to retrieve, defaults to 0 (optional)
        :return: The subkey object.
        '''
        if receiveAddr == changeAddr:
            raise ValueError("Either choose receiving address or change address, not both!")

        key = self.Network.parse(self.publicKey) #direct version (xpub=legacy, ypub=segwit, zpub=native segwit)
        subkey = key.subkey_for_path("{0}/{1}".format("0" if receiveAddr else "1", str(number)))
        return subkey

    def generateAddresses(self, func, receiveAddr:bool=True, changeAddr:bool=False, numAddresses=1000):
        '''
        Generate a list of addresses
        
        :param func: the function that generates the address
        :param receiveAddr: if True, generate a receive address. If False, then generate a change
        address, defaults to True
        :type receiveAddr: bool (optional)
        :param changeAddr: if True, generate a change address, defaults to False
        :type changeAddr: bool (optional)
        :param numAddresses: the number of addresses to generate, defaults to 1000 (optional)
        :return: A generator object.
        '''
        # returns a generator object
        counter = 0
        while True:
            if (counter > numAddresses): 
                return
            yield func(receiveAddr, changeAddr, counter)
            counter += 1

    def generateAddress(self, receiveAddr:bool=True, changeAddr:bool=False, number=0):
        '''
        If you want to generate an address, call this function
        
        :param receiveAddr: If True, the address will be marked as a receiving address. If False, it will be
        marked as a change address, defaults to True
        :type receiveAddr: bool (optional)
        :param changeAddr: If True, the address will be for change (rather than receive), defaults to False
        :type changeAddr: bool (optional)
        :param number: The index of the subkey to generate, defaults to 0 (optional)
        :return: The address of the subkey.
        '''
        subkey = self._getSubkey(receiveAddr, changeAddr, number)
        return subkey.address()

    def generateSegwitAddressFromXpub(self, receiveAddr:bool=True, changeAddr:bool=False, number=0):
        "For Ledger Xpubs that are actually used as ypubs. Alternative: Convert to ypub: https://jlopp.github.io/xpub-converter/"
        subkey = self._getSubkey(receiveAddr, changeAddr, number)
        #(#P2WPKH in P2SH / ypub) -->pycoin/key/BIP49Node.py
        script = self.Network.contract.for_p2pkh_wit(subkey.hash160(is_compressed=True))
        return self.Network.address.for_p2s(script)

    def generateNativeSegwitAddressFromXpub(self, receiveAddr:bool=True, changeAddr:bool=False, number=0):
        "For Ledger Xpubs that are actually used as ypubs"
        subkey = self._getSubkey(receiveAddr, changeAddr, number)
        #(#P2WPKH) -->pycoin/key/BIP84Node.py
        return self.Network.address.for_p2pkh_wit(subkey.hash160(is_compressed=True))
    
    def getNumTxForAddress(self, address, txData):
        pass

    def _getRawTxsForAddress(self, address, offset=None):
        print("Querying address {}".format(address))
        return blockcypher.get_address_details(address, coin_symbol=self.Network.symbol.lower())
    
    def _getRawTxDetails(self, txHash):
        #print("Querying Tx {}".format(txHash))
        return blockcypher.get_transaction_details(txHash, coin_symbol=self.Network.symbol.lower())

    def _query(self, url):
        '''
        Query the data. Takes a url as an input, calls the url, and returns the data
        
        :param url: the url to query
        :return: A dictionary of data.
        '''
        response = requests.get(url)
        print("Calling {}".format(url))
        if response.status_code != 200:
            raise BaseException("Wrong output")
        print(response.ok)
        print(response.status_code)
        data = response.json()
        time.sleep(10.5) #rate limit blockchain.info
        return data
    
    def _getTransactions(self, addressGenerator, offset=None, startTime=None, receiving=True):
        while(True):
            address = next(addressGenerator)
            data = self._getRawTxsForAddress(address, offset)
            num = data["n_tx"]
            if num == 0:
                break
            for elem in data["txrefs"]: #txs blockchain info
                txHash = elem["tx_hash"]
                change = satoshi_to_btc(elem["value"])
                # Check for out or inbound transaction
                isOut = elem["tx_output_n"] < 0
                isIn = elem["tx_output_n"] >= 0
                txFound = False

                if self.txList.hasTx(txHash):
                    t, idx = self.txList.fromTxHash(txHash)
                    txFound = True
                    #self.txList[idx] = t
                else:
                    # Fill new transaction object
                    t = Transaction()
                    t.datetime = elem["confirmed"]
                    t.txHash = txHash
                    
                if isIn and receiving:
                        t.posIn += Position(change, self.Network.symbol)
                if isOut:
                        t.posOut += Position(change, self.Network.symbol)
                if isIn and not(receiving):
                        t.posOut += Position(-change, self.Network.symbol)
                
                if not(txFound):
                    self.txList.append(t)


        return self.txList

    def _getAllTransactions(self, addressType:AddresType = AddresType.LEGACY):

        if addressType == AddresType.LEGACY:
            func = self.generateAddress

        elif addressType == AddresType.SEGWIT:
            func = self.generateSegwitAddressFromXpub
        
        elif addressType == AddresType.NATIVE_SEGWIT:
            func = self.generateNativeSegwitAddressFromXpub

        addressGenerator = self.generateAddresses(func, receiveAddr=True, changeAddr=False) 
        self._getTransactions(addressGenerator)
        addressGenerator = self.generateAddresses(func, receiveAddr=False, changeAddr=True) 
        self._getTransactions(addressGenerator, receiving=False)
        
        self.txList.sort(key=lambda r: r.datetime)


    def getTransactions(self, startTime=None, offset=None) -> 'TransactionList':
        #We test all 3 address types in case we have a ypub/zpub key as xpub key (as the Ledger software is doing)
        self._getAllTransactions(addressType=AddresType.LEGACY)
        time.sleep(5)
        self._getAllTransactions(addressType=AddresType.SEGWIT)
        time.sleep(5)
        self._getAllTransactions(addressType=AddresType.NATIVE_SEGWIT)

        #Sort
        self.txList.sort(key=lambda r: r.datetime)

        # Add fees only to outgoing transactions
        for tx in self.txList:
            if tx.isOutBound() and tx.fee.amount == 0:
                details = self._getRawTxDetails(tx.txHash)
                tx.fee = Fee( satoshi_to_btc(details["fees"]), self.Network.symbol)
            print(tx)

        return self.txList
        
