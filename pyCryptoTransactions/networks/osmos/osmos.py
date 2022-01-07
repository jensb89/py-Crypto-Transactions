from pyCryptoTransactions.networks.cosmos.cosmos import CosmosChain

class OsmosChain(CosmosChain):

    def __init__(self, address):
        super().__init__(address)

        self._apiAdress = "https://api-osmosis.cosmostation.io/v1/"
        self.chain = "osmosis-1"
        self.ibcTokenApiAddress = "https://api-utility.cosmostation.io/v1//ibc/tokens/osmosis-1"
        self.unit = "OSMO"
        self._getAllIBCTokens()
    
    @property
    def pathToMemo(self):
        return ["data","tx","body","memo"]
    
    @property
    def pathToFee(self):
        return ["data","tx","auth_info","fee","amount",0,"amount"]
    
    @property
    def pathToFeeCurrency(self):
        return ["data","tx","auth_info","fee","amount",0,"denom"]