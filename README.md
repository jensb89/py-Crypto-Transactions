# py-Crypto-Transactions

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