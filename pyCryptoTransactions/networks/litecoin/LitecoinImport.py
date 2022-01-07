from pycoin.networks.registry import network_for_netcode
from pycoin.networks.bitcoinish import create_bitcoinish_network
import blockcypher

from pyCryptoTransactions.networks.bitcoin import BitcoinImport

class LitecoinImport(BitcoinImport):
    Network = network_for_netcode("LTC")

    def __init__(self, publicKey):
        super().__init__(publicKey)

        print(publicKey[0:4])
        if publicKey[0:4].lower() == "xpub":
            print("detected")
            self.Network = create_bitcoinish_network(
                        network_name="Litecoin", symbol="LTC", subnet_name="mainnet",
                        wif_prefix_hex="b0", sec_prefix="LTCSEC:", address_prefix_hex="30", pay_to_script_prefix_hex="32",
                        bip32_prv_prefix_hex="019d9cfe", bip32_pub_prefix_hex="0488B21E", bech32_hrp="ltc") # changed: bip32_pub_prefix_hex from bitcoin
    



