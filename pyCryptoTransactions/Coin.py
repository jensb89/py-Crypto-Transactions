class Coin(object):
    
    @property
    def symbol(self) -> str:
        """
        The symbol
        """
        return self.__symbol
    
    @symbol.setter
    def symbol(self, value:str):
       self.__symbol = value.upper()

    @property
    def name(self) -> str:
        """
        The name
        """
        return self.__name
    
    @name.setter
    def name(self, value):
       self.__name = value

    @property
    def id(self) -> str:
        """
        The id
        """
        return self.__id
    
    @id.setter
    def id(self, value):
       self.__id = value

    @property
    def contractAddress(self) -> str:
        """
        The contract address of the coin
        """
        return self.__contractAddress
    
    @contractAddress.setter
    def contractAddress(self, value):
       self.__contractAddress = value
    
    def __init__(self, symbol:str, name=None, id=None, contractAddress = None ) -> None:
        super().__init__()
        self.symbol = symbol
        self.name = name
        self.id = id 
        self.contractAddress = contractAddress

    def __repr__(self) -> str:
        return self.__symbol
    

    