# py-Crypto-Transactions

[![PyPI](https://badge.fury.io/py/pycryptotransactions.svg)](https://badge.fury.io/py/pycryptotransactions)
![PyPI - Downloads](https://img.shields.io/pypi/dm/pycryptotransactions)
![GitHub](https://img.shields.io/github/license/pcko1/pycryptotransactions)
[![Python 3.8](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-310/)
![GitHub Issues](https://img.shields.io/github/issues/jensb89/py-Crypto-Transactions)


A python package to query crypto transaction from various blockchains and exchanges
to build your own portfolio app!

pyCryptoTransactions also supports a few exporters, such that data can be imported e.g. at Koinly or Accointing.

Note: Very elary alpha version!

## Install
Use pip:
 * pip install pyCryptoTransactions (NOTE: make sure to use camelCase name like this and not pycryptotransactions)
Or use poetry 
Or install directly by cloning the git repo
## Supported Blockchains
 * Bitcoin
 * Litecoin
 * Cosmos
 * Thorchain
 * Osmos
 * Iota
 * Persistence
 * Ethereum (soon)
 * Bsc (soon)

## Supported exchanges
 * Binance (support for exported CSVs, no API yet)
 * Coinbase (Oauth Api)
 * Coinbase Pro (soon)

## Examples
```
t = LitecoinImport("xpub...")
t.getTransactions()`
```

```
t = CosmosChain("cosmos....")
txs = t.getTransactions()
print(txs)
df = txs.toPandasDataframe()
df.to_csv("atom_test.csv")
print(txs.calculateBalance())
a = AccointingExporter(txs)
a.exportToExcel("atom_accointing.xlsx")
```