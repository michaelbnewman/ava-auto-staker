#!/usr/bin/python3

"""
https://github.com/michaelbnewman/ava-auto-staker

Usage: ./ava_auto_staker.py
"""

import configparser
from datetime import datetime, timedelta
from requests.exceptions import ConnectionError
import requests
import random
from simplejson.errors import JSONDecodeError
from sys import exit
from time import sleep
from uuid import uuid4

config = configparser.ConfigParser()
config.read("config.ini")

staking_amount = int(config["STAKING"]["amount_nAVA"])
staking_duration = int(config["STAKING"]["duration_days"])

url = config["RPC"]["url"] + "{}"
platform_payerNonce = 0

def printlog(message):
    now_text = datetime.now().isoformat(" ")
    print("[{}] {}".format(now_text, message))

# --- #

# Create keystore user

username = config["KEYSTORE"]["username"]
password = config["KEYSTORE"]["password"]
if (not username) or (not password):
    jsonrpc_path = "/ext/keystore"
    method = "keystore.createUser"
    username = "USER-" + uuid4().hex
    password = "PASS-" + uuid4().urn
    payload = {
         "jsonrpc":"2.0",
         "id":1,
         "method":"{}".format(method),
         "params":{
             "username":"{}".format(username),
             "password":"{}".format(password)
         }
    }
    while True:
        try:
            response = requests.post(url.format(jsonrpc_path), json=payload).json()
            # (Pdb) response
            # {'jsonrpc': '2.0', 'result': {'success': True}, 'id': 1}
            assert response["result"]["success"] == True
            printlog("/ext/keystore: keystore.createUser: username {} password {}".format(username, password))
            break
        except KeyError:
            exit("/ext/keystore: keystore.createUser: Failed: {}".format(response))
        except ConnectionError:
            sleep(1.0)
else:
    printlog("/ext/keystore: Using existing username {} password {}".format(username, password))

# --- #

# Get Node ID

jsonrpc_path = "/ext/admin"
method = "admin.getNodeID"
payload = {
    "jsonrpc":"2.0",
    "id":1,
    "method":"{}".format(method),
    "params":{}
}
node_id = None
while not node_id:
    try:
        response = requests.post(url.format(jsonrpc_path), json=payload).json()
        # (Pdb) response
        # {"jsonrpc":"2.0","result":{"nodeID":"7LAykkZSYCGaBhacUgG3c5NwATALLYgiw"},"id":1}
        node_id = response["result"]["nodeID"]
        printlog("{}: {}: {}".format(jsonrpc_path, method, node_id))
    except JSONDecodeError:
        sleep(1.0)
    except KeyError:
        printlog("{}: {}: FAILED: {}".format(jsonrpc_path, method, response))
        sleep(3.0)
    except ConnectionError:
        sleep(1.0)

# --- #

# Create X-address.

x_address = config["X-CHAIN"]["address"]
if not x_address:
    jsonrpc_path = "/ext/bc/X"
    method = "avm.createAddress"
    payload = {
        "jsonrpc":"2.0",
        "id":1,
        "method":"{}".format(method),
        "params":{
            "username":"{}".format(username),
            "password":"{}".format(password)
        }
    }
    x_address = None
    while not x_address:
        try:
            response = requests.post(url.format(jsonrpc_path), json=payload).json()
            # (Pdb) response
            # {'jsonrpc': '2.0', 'result': {'address': 'X-HP7Do5SP3Z9MmcMkBJKw7EPoPZmJAihQ3'}, 'id': 1}
            x_address = response["result"]["address"]
            printlog("{}: {}: {}".format(jsonrpc_path, method, x_address))
        except JSONDecodeError:
            sleep(1.0)
        except KeyError:
            exit("{}: {}: FAILED: {}".format(jsonrpc_path, method, response))

# --- #

# Create P-address.

p_address = config["P-CHAIN"]["address"]
if not p_address:
    jsonrpc_path = "/ext/P"
    method = "platform.createAccount"
    payload = {
        "jsonrpc": "2.0",
        "id":1,
        "method": "{}".format(method),
        "params": {
            "username": "{}".format(username),
            "password": "{}".format(password)
        }
    }
    response = requests.post(url.format(jsonrpc_path), json=payload).json()
    # (Pdb) response
    # {"jsonrpc":"2.0","result":{"address":"BCLMV6ZM36ApYMPwZwsTaRamjSJHkA7yT"},"id":1}
    try:
        p_address = response["result"]["address"]
        printlog("{}: {}: {}".format(jsonrpc_path, method, p_address))
    except KeyError:
        exit("{}: {}: FAILED: {}".format(jsonrpc_path, method, response))

# --- #

# Check peers count to verify connected to network.

peers = []
while not peers:
    jsonrpc_path = "/ext/admin"
    method = "admin.peers"
    payload = {
        "jsonrpc": "2.0",
        "id":1,
        "method": "{}".format(method)
    }
    response = requests.post(url.format(jsonrpc_path), json=payload).json()
    # (Pdb) response
    # {"jsonrpc":"2.0","result":{"peers":["107.23.241.199:21001","167.172.181.170:9651","3.227.207.132:21001","34.207.133.167:21001","54.197.215.186:21001","78.47.30.91:9651","82.59.54.86:9651","95.179.163.191:9651"]},"id":1}
    peers = response["result"]["peers"]
    if not peers:
        printlog("{}: {}: No peers found. Retrying in 3 seconds...".format(jsonrpc_path, method))
        sleep(3)
    else:
        printlog("{}: {}: Connected to {} peers.".format(jsonrpc_path, method, len(peers)))

# --- #

# Check validators count to verify network is operational.

validators = []
while not validators:
    jsonrpc_path = "/ext/P"
    method = "platform.getCurrentValidators"
    payload = {
        "jsonrpc": "2.0",
        "id":1,
        "method": "{}".format(method)
    }
    response = requests.post(url.format(jsonrpc_path), json=payload).json()
    # (Pdb) response
    # {"jsonrpc":"2.0","result":{"validators":[
    #   {"startTime":"1587321008","endtime":"1587407742","stakeAmount":"10000","id":"7LAykkZSYCGaBhacUgG3c5NwATALLYgiw"},
    #   {"startTime":"1587169531","endtime":"1587774031","stakeAmount":"100000","id":"5Gyq9q8f2yX3tFze6MFj1VfDkFQtUjthk"},
    validators = response["result"]["validators"]
    if not validators:
        printlog("{}: {}: No validators found. Retrying in 3 seconds...".format(jsonrpc_path, method))
        sleep(3)
    else:
        printlog("{}: {}: There are {} validators.".format(jsonrpc_path, method, len(validators)))

# --- #

# Show X-address starting balance (normally is zero).

jsonrpc_path = "/ext/bc/X"
method = "avm.getBalance"
payload = {
    "jsonrpc": "2.0",
    "id":1,
    "method": "{}".format(method),
    "params": {
        "address": "{}".format(x_address),
        "assetID": "AVA"
    }
}
response = requests.post(url.format(jsonrpc_path), json=payload).json()
try:
    x_balance = int(response["result"]["balance"])
    printlog("{}: {}: {} nAVA for {}".format(jsonrpc_path, method, x_balance, x_address))
except KeyError:
    exit("{}: {}: FAILED: {}".format(jsonrpc_path, method, response))

# If insufficient funds to stake, prompt user to go to faucet to fund X-address, and wait.
# Once X-address sufficiently funded, show new balance and proceed.
if x_balance < staking_amount:
    printlog("Please get more funds at https://faucet.ava.network/?address={}".format(x_address))
    printlog("To verify transaction activity, see: https://explorer.ava.network/address/{}".format(x_address[2:]))
while x_balance < staking_amount:
    try:
        response = requests.post(url.format(jsonrpc_path), json=payload).json()
        x_balance = int(response["result"]["balance"])
        sleep(0.5)
    except ConnectionError:
        printlog("{}: {}: FAILED: Connection Error. Sleeping 60 seconds...".format(jsonrpc_path, method))
        sleep(60)
    except KeyError:
        exit("{}: {}: FAILED: {}".format(jsonrpc_path, method, response))
printlog("{}: {}: {} nAVA for {}".format(jsonrpc_path, method, x_balance, x_address))

# --- #

# Fund P-chain

jsonrpc_path = "/ext/bc/X"
method = "avm.exportAVA"
payload = {
    "jsonrpc":"2.0",
    "id":1,
    "method":"{}".format(method),
    "params":{
        "to":"{}".format(p_address),
        "amount": staking_amount,
        "username":"{}".format(username),
        "password":"{}".format(password)
    }
}
response = requests.post(url.format(jsonrpc_path), json=payload).json()
# (Pdb) response
# {"jsonrpc":"2.0","result":{"txID":"29VLGkAXjVnFvQyqPtsrXnkWUzMWv2gQCbo1NvsPhKhHPyd6Pa"},"id":1}
try:
    txID = response["result"]["txID"]
    printlog("{}: {}: txID {}".format(jsonrpc_path, method, txID))
except KeyError:
    exit("{}: {}: FAILED: {}".format(jsonrpc_path, method, response))

txStatus = "Unknown"
while txStatus != "Accepted":
    jsonrpc_path = "/ext/bc/X"
    method = "avm.getTxStatus"
    payload = {
        "jsonrpc":"2.0",
        "id":1,
        "method":"{}".format(method),
        "params":{
            "txID":"{}".format(txID)
        }
    }
    # (Pdb) response
    # {"jsonrpc":"2.0","result":{"status":"Processing"},"id":6}
    # {"jsonrpc":"2.0","result":{"status":"Accepted"},"id":6}
    response = requests.post(url.format(jsonrpc_path), json=payload).json()
    try:
        txStatus = response["result"]["status"]
        if txStatus == "Accepted":
            printlog("{}: {}: {}".format(jsonrpc_path, method, txStatus))
            break
        sleep(0.5)
    except KeyError:
        exit("{}: {}: FAILED: {}".format(jsonrpc_path, method, response))

jsonrpc_path = "/ext/bc/X"
method = "avm.getBalance"
payload = {
    "jsonrpc": "2.0",
    "id":1,
    "method": "{}".format(method),
    "params": {
        "address": "{}".format(x_address),
        "assetID": "AVA"
    }
}
response = requests.post(url.format(jsonrpc_path), json=payload).json()
try:
    x_balance = int(response["result"]["balance"])
    printlog("{}: {}: {} nAVA for {}".format(jsonrpc_path, method, x_balance, x_address))
except KeyError:
    exit("{}: {}: FAILED: {}".format(jsonrpc_path, method, response))

##

platform_payerNonce = platform_payerNonce + 1
jsonrpc_path = "/ext/bc/P"
method = "platform.importAVA"
payload = {
    "jsonrpc":"2.0",
    "id":1,
    "method":"{}".format(method),
    "params":{
        "to":"{}".format(p_address),
        "amount": staking_amount,
        "payerNonce":platform_payerNonce,
        "username":"{}".format(username),
        "password":"{}".format(password)
    }
}
response = requests.post(url.format(jsonrpc_path), json=payload).json()
# (Pdb) response
# {"jsonrpc":"2.0","result":{"tx":"111CjpaL8zPV3bvDtAGL1gjMNmdENuGQ2WmnNSpw5ZdNxHWNwGmnq7aDEyXnAQ8ACoZhDLcD2D6g673SZmfC1E8xwxQGnPEo56afFeRWREbxzLbLspNLi4fCM4S5U9XU7ojmoJbsgjmAhgtaqAYJYKyg8"},"id":1}
try:
    tx = response["result"]["tx"]
    printlog("{}: {}: tx created: {}".format(jsonrpc_path, method, tx))
except KeyError:
    exit("{}: {}: FAILED: {}".format(jsonrpc_path, method, response))

jsonrpc_path = "/ext/bc/P"
method = "platform.issueTx"
payload = {
    "jsonrpc":"2.0",
    "id":1,
    "method":"{}".format(method),
    "params":{
        "tx":"{}".format(tx)
    }
}
response = requests.post(url.format(jsonrpc_path), json=payload).json()
# (Pdb) response
# {"jsonrpc":"2.0","result":{"txID":"2qFkSVZq9hTpGSHVH7g4MDehJML4kuLCn9v78ovRDV83JHzaeW"},"id":1}
try:
    txID = response["result"]["txID"]
    printlog("{}: {}: txID {}".format(jsonrpc_path, method, txID))
except KeyError:
    exit("{}: {}: FAILED: {}".format(jsonrpc_path, method, response))

##

jsonrpc_path = "/ext/bc/P"

method = "platform.getAccount"
payload = {
    "jsonrpc": "2.0",
    "id":1,
    "method": "{}".format(method),
    "params": {
        "address": "{}".format(p_address),
        "assetID": "AVA"
    }
}
p_balance = 0
while p_balance < staking_amount:
    try:
        response = requests.post(url.format(jsonrpc_path), json=payload).json()
        p_balance = int(response["result"]["balance"])
        if p_balance < staking_amount:
            sleep(0.5)
        else:
            break
    except ConnectionError:
        printlog("{}: {}: FAILED: Connection Error. Sleeping 60 seconds...".format(jsonrpc_path, method))
        sleep(60)
    except KeyError:
        exit("{}: {}: FAILED: {}".format(jsonrpc_path, method, response))
printlog("{}: {}: {} nAVA for {}".format(jsonrpc_path, method, p_balance, p_address))

# --- #

# Create the Unsigned Transaction

start_time = int((datetime.now() + timedelta(minutes=10)).timestamp())
end_time = int((datetime.now() + timedelta(days=staking_duration, minutes=15)).timestamp())

platform_payerNonce = platform_payerNonce + 1
jsonrpc_path = "/ext/P"
method = "platform.addDefaultSubnetValidator"
payload = {
    "jsonrpc":"2.0",
    "id":1,
    "method":"{}".format(method),
    "params":{
        "id":"{}".format(node_id),
        "destination":"{}".format(p_address),
        "stakeAmount": staking_amount,
        "startTime": start_time,
        "endTime": end_time,
        "payerNonce":platform_payerNonce
    }
}
response = requests.post(url.format(jsonrpc_path), json=payload).json()
# (Pdb) response
# {"jsonrpc":"2.0","result":{"unsignedTx":"1112P94uoPa7nmv2E1YFfRUfvY8VTgDu2SPqdY6jBpcJcPtmf8WGro8a8P2rxjBa1KJyjtk4yiGxpRFdwfEEACF51Xs5KWKRFnLw2WrJpjFBFMG5GaPXD3qr1QzTas8dMCMx6E52EjSm3U6WakWxFAiaySwJKoFdgj2kPeEaneEQTLGdFmjBWjJy48adAtdnj61jBe6UZj7nuyrj"},"id":1}
try:
    unsignedTx = response["result"]["unsignedTx"]
    printlog("{}: {}: unsigntedTx created: {}".format(jsonrpc_path, method, unsignedTx))
except KeyError:
    exit("{}: {}: FAILED: {}".format(jsonrpc_path, method, response))

# --- #

# Sign the Transaction

jsonrpc_path = "/ext/P"
method = "platform.sign"
payload = {
    "jsonrpc":"2.0",
    "id":1,
    "method":"{}".format(method),
    "params":{
        "tx":"{}".format(unsignedTx),
        "signer":"{}".format(p_address),
        "username":"{}".format(username),
        "password":"{}".format(password)
    }
}
response = requests.post(url.format(jsonrpc_path), json=payload).json()
# (Pdb) response
# {"jsonrpc":"2.0","result":{"tx":"1112P94uoPa7nmv2E1YFfRUfvY8VTgDu2SPqdY6jBpcJcPtmf8WGro8a8P2rxjBa1KJyjtk4yiGxpRFdwfEEACF51Xs5KWKRFnLw2WrJpjFBFMG5GcWbfQUo5X3xUJvPNFRxhauyJ9yFfiQh88S8n2AKP9SmA5EFLR8LZ9m1RXnSTbvnozxgHtgV2p9AXxcf9uSKEt2wHHbPmRH2"},"id":2}
try:
    tx = response["result"]["tx"]
    printlog("{}: {}: tx created: {}".format(jsonrpc_path, method, tx))
except KeyError:
    exit("{}: {}: FAILED: {}".format(jsonrpc_path, method, response))

# --- #

# Issue the Transaction

jsonrpc_path = "/ext/P"
method = "platform.issueTx"
payload = {
    "jsonrpc":"2.0",
    "id":1,
    "method":"{}".format(method),
    "params":{
        "tx":"{}".format(tx)
    }
}
response = requests.post(url.format(jsonrpc_path), json=payload).json()
# (Pdb) response
# {"jsonrpc":"2.0","result":{"txID":"2qFkSVZq9hTpGSHVH7g4MDehJML4kuLCn9v78ovRDV83JHzaeW"},"id":1}
try:
    txID = response["result"]["txID"]
    printlog("{}: {}: txID {}".format(jsonrpc_path, method, txID))
except KeyError:
    exit("{}: {}: FAILED: {}".format(jsonrpc_path, method, response))

# --- #

# Verify Success

jsonrpc_path = "/ext/P"
method = "platform.getPendingValidators"
payload = {
    "jsonrpc":"2.0",
    "id":1,
    "method":"{}".format(method),
    "params":{}
}
pending_validators = []
node_found = False
while not node_found:
    try:
        response = requests.post(url.format(jsonrpc_path), json=payload).json()
        # (Pdb) response
        # {"jsonrpc":"2.0","result":{"validators":[{"startTime":"1587321008","endtime":"1587407742","stakeAmount":"10000","id":"7LAykkZSYCGaBhacUgG3c5NwATALLYgiw"}]},"id":1}
        validators = response["result"]["validators"]
        for validator in validators:
            if validator["id"] == node_id:
                printlog("{}: {}: node_id {} successfully found in pending validators list as: {}".format(jsonrpc_path, method, node_id, validator))
                node_found = True
        if not node_found:
            printlog("{}: {}: node_id {} not yet found in pending validators list {}".format(jsonrpc_path, method, node_id, validators))
            sleep(60)
    except ConnectionError:
        printlog("{}: {}: FAILED: Connection Error. Sleeping 60 seconds...".format(jsonrpc_path, method))
        sleep(60)
    except KeyError:
        exit("{}: {}: FAILED: {}".format(jsonrpc_path, method, response))

# --- #

while True:
    try:
        jsonrpc_path = "/ext/admin"
        method = "admin.peers"
        payload = {
            "jsonrpc": "2.0",
            "id":1,
            "method": "{}".format(method)
        }
        response = requests.post(url.format(jsonrpc_path), json=payload).json()
        # (Pdb) response
        # {"jsonrpc":"2.0","result":{"peers":["107.23.241.199:21001","167.172.181.170:9651","3.227.207.132:21001","34.207.133.167:21001","54.197.215.186:21001","78.47.30.91:9651","82.59.54.86:9651","95.179.163.191:9651"]},"id":1}
        peers = response["result"]["peers"]

        jsonrpc_path = "/ext/P"
        method = "platform.getCurrentValidators"
        payload = {
            "jsonrpc": "2.0",
            "id":1,
            "method": "{}".format(method)
        }
        response = requests.post(url.format(jsonrpc_path), json=payload).json()
        # (Pdb) response
        # {"jsonrpc":"2.0","result":{"validators":[
        #   {"startTime":"1587321008","endtime":"1587407742","stakeAmount":"10000","id":"7LAykkZSYCGaBhacUgG3c5NwATALLYgiw"},
        #   {"startTime":"1587169531","endtime":"1587774031","stakeAmount":"100000","id":"5Gyq9q8f2yX3tFze6MFj1VfDkFQtUjthk"},
        validators = response["result"]["validators"]
        if not validators:
            printlog("{}: {}: No validators found. Retrying in 60 seconds...".format(jsonrpc_path, method))
            sleep(60)
        else:
            validator_found = False
            for validator in validators:
                if validator["id"] == node_id:
                    validator_found = True
            if validator_found:
                printlog("{}: {}: There are {} peers, and {} validators including node_id {}.".format(jsonrpc_path, method, len(peers), len(validators), node_id))                
            else:
                printlog("{}: {}: There are {} peers, and {} validators but node_id {} not yet found.".format(jsonrpc_path, method, len(peers), len(validators), node_id))                
            sleep(600)
    except ConnectionError:
        printlog("{}: {}: FAILED: Connection Error. Sleeping 60 seconds...".format(jsonrpc_path, method))
        sleep(60)
