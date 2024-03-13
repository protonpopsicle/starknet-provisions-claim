# starknet provisions claim

See https://github.com/starknet-io/provisions-data/

Python script to generate a signed transaction to claim STRK allocation outside of the web portal and send it to the Ethereum blockchain.

## Dependencies

`$ pip3 install web3`

Inspect the JSON files located here: https://github.com/starknet-io/provisions-data/tree/main/eth and determine which contains the Merkle path corresponding to your identity (ethereum address). Download this file to same directory as script and rename to `data.json`.

## Usage Example

`$ PRIVATE_KEY=0xBLAH ./transaction.py --eth_node_url="http://127.0.0.1:8545" --starknet_address="0xBLAH"`
