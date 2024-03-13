#!/usr/bin/env python3

import argparse
import json
import os
from web3 import Web3


# impliments https://github.com/starknet-io/provisions-data

contract_address = "0xc662c410C0ECf747543f5bA90660f6ABeBD9C8c4"

# contract ABI defining sendMessageToL2 function copied from https://etherscan.io/address/0x16938e4b59297060484fa56a12594d8d6f4177e8#code
abi = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "toAddress", "type": "uint256"},
            {"internalType": "uint256", "name": "selector", "type": "uint256"},
            {"internalType": "uint256[]", "name": "payload", "type": "uint256[]"},
        ],
        "name": "sendMessageToL2",
        "outputs": [
            {"internalType": "bytes32", "name": "", "type": "bytes32"},
            {"internalType": "uint256", "name": "", "type": "uint256"},
        ],
        "stateMutability": "payable",
        "type": "function"
    }
]

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--eth_node_url', help='HTTP endpoint of an ethereum node you want to connect to', required=True)
    parser.add_argument('--starknet_address', type=str, help='Your starknet address', required=True)
    args = parser.parse_args()

    private_key = os.environ.get('PRIVATE_KEY')
    assert private_key is not None, 'You must set PRIVATE_KEY environment variable'
    assert private_key.startswith('0x'), 'Private key must start with 0x hex prefix'
    assert args.starknet_address.startswith('0x'), 'Starknet address must start with 0x hex prefix'

    provisions_data = {}

    print('connecting...')
    w3 = Web3(Web3.HTTPProvider(args.eth_node_url))
    assert(w3.is_connected())
    print('connected!')

    eth_address = w3.eth.account.from_key(private_key).address
    print('ethereum address:', eth_address)  # derived from private key

    # assumes data.json is one of these files https://github.com/starknet-io/provisions-data/tree/main/eth
    # which contains your ethereum address and is present in the same directory as this script
    with open('data.json') as f:
        for d in json.load(f)['eligibles']:
            if w3.to_checksum_address(d['identity']) == eth_address:
                provisions_data = d
                break

    assert provisions_data, 'ethereum address not found in list of eligbles'
    balance = int(provisions_data['amount']) * 10**18  # convert to fri units
    merkle_path = provisions_data['merkle_path']

    contract = w3.eth.contract(address=contract_address, abi=abi)

    # init chain id needed to build the transaction for replay protection
    chain_id = w3.eth.chain_id  # should be 1 for mainnet

    # calculate fees following EIP-1159
    base_fee = w3.eth.fee_history(1, 'latest', [10, 90])['baseFeePerGas'][0]
    max_priority_fee =  1000000000  # tip paid to validator, edit to taste
    max_fee = (2 * base_fee) + max_priority_fee  # enough to cover max network fee + priority fee
    print('baseFeePerGas:', base_fee)
    print('maxPriorityFeePerGas:', max_priority_fee)
    print('maxFee:', max_fee)
    
    msg_value = 3000 * base_fee  # the transaction must have a correct payable amount: the invoked function costs roughly 3000 gas

    # payload formatted according to ABI spec for sendMessageToL2 function
    payload=(
        int(eth_address, 16),
        balance,
        0,
        int(provisions_data['merkle_index']),
        len(merkle_path), *[int(x, 16) for x in merkle_path],
        int(args.starknet_address, 16),
    )
    print()
    print('payload:', payload)
    print()
    unsent_tx = contract.functions.sendMessageToL2(
        toAddress=int('0x071808540ed1139bcc8bb55eb975e8168758f2a342ce3f22c512a1c8da1b84dc', 16),
        selector=int('0x00828430c65c40cba334d4723a4c5c02a62f612d73d564a1c7dc146f1d0053f9', 16),
        payload=payload,
    ).build_transaction({
        'chainId': chain_id,
        'from': eth_address,
        'nonce': w3.eth.get_transaction_count(eth_address),
        'value': msg_value,
        'maxFeePerGas': max_fee,
        'maxPriorityFeePerGas': max_priority_fee,
    })
    print('transaction:', unsent_tx)
    print()

    # sign transaction
    signed_tx = w3.eth.account.sign_transaction(unsent_tx, private_key=private_key)
    print('signed transaction:', signed_tx.rawTransaction)

    print()
    if input('do you want to really send transaction? (yes/no): ') != 'yes':
        exit()
    
    print('sending...')
    send_tx = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    print('sent')

    # wait for transaction receipt
    print('waiting for transaction receipt...')
    tx_receipt = w3.eth.wait_for_transaction_receipt(send_tx)
    print('transaction receipt:', tx_receipt)
