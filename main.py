# this script will monitor an address outgoing transactions (sending)
#if the address sends a a specific token (customizable and can be more than one) the script wil send those addresses a token of your choice!!
# ensure you have a file transactions.csv in the same folder as script.
#it needs the following headers, time, address, amount (all lower caps)
#rows can be empty
#Cobbled together by Flying Pig to help distribute Comet to our ADA friends :)

import requests
import time as sleep
from datetime import datetime
from ergpy import helper_functions, appkit
import csv

node_url = "http://213.239.193.208:9053"
wallet_mnemonic = "" 

#----some examples below. One is RSN (will monitor any address sending rsADA from cardano to ERGO.The other is spectrum (sending $lambo to any address buying RSN)

address_to_monitor= "nB3L2PD3J4rMmyGk7nnNdESpPXxhPRQ4t1chF8LTXtceMQjKCEgL2pFjPY6cehGjyEFZyHEomBTFXZyqfonvxDozrTtK5JzatD8SdmcPeJNWPvdRb5UxEMXE4WQtpAFzt2veT8Z6bmoWN" # Rosenbridge
token_to_monitor = ["e023c5f382b6e96fbd878f6811aac73345489032157ad5affb84aefd4956c297"] #tokens you want to monitor, this is rsAda. Can be more than 1

#address_to_monitor="5vSUZRZbdVbnk4sJWjg2uhL94VZWRg4iatK9VgMChufzUgdihgvhR8yWSUEJKszzV7Vmi6K8hCyKTNhUaiP8p5ko6YEU9yfHpjVuXdQ4i5p4cRCzch6ZiqWrNukYjv7Vs5jvBwqg5hcEJ8u1eerr537YLWUoxxi1M4vQxuaCihzPKMt8NDXP4WcbN6mfNxxLZeGBvsHVvVmina5THaECosCWozKJFBnscjhpr3AJsdaL8evXAvPfEjGhVMoTKXAb2ZGGRmR8g1eZshaHmgTg2imSiaoXU5eiF3HvBnDuawaCtt674ikZ3oZdekqswcVPGMwqqUKVsGY4QuFeQoGwRkMqEYTdV2UDMMsfrjrBYQYKUBFMwsQGMNBL1VoY78aotXzdeqJCBVKbQdD3ZZWvukhSe4xrz8tcF3PoxpysDLt89boMqZJtGEHTV9UBTBEac6sDyQP693qT3nKaErN8TCXrJBUmHPqKozAg9bwxTqMYkpmb9iVKLSoJxG7MjAj72SRbcqQfNCVTztSwN3cRxSrVtz4p87jNFbVtFzhPg7UqDwNFTaasySCqM" #Spectrum
#token_to_monitor =["8b08cdd5449a9592a9e79711d7d79249d7a03c535d17efaee83e216e80a44c4b","0cd8c9f416e5b1ca9f986a7f10a84191dfb85941619e49e53c0dc30ebf83324b","e023c5f382b6e96fbd878f6811aac73345489032157ad5affb84aefd4956c297"] # Token you want to monitor. This is RSN. Can be more than one.

no_transactions_to_fetch = 100 #fetches last x transactions from address to monitor.
check_interval = 300  #seconds between each check.
blacklist = ['9hp3fH6LkT5tkKqrYUXX4J2D1TEYcBht62RhU6EXnSXCdrBH5jQ','9iHgXoqrq6mTqTeUUY6XQs1Ea6yjWsM8YdoipKDXzp5NJ6su3zM'] #addresses to ignore and not reward. These 2 are related to rsn contracts (guards/similar)
csv_filename = 'transactions.csv' # will save any matching addresses to this file and check any new addresses to ensure no one gets sent tokens twice!
csv_tx_sent = 'tx_sent.csv' # csv to store submitted reward transactions
testing = False #set to true if you want to test script. this will send tokens to testing address instead of true recipient
testing_address ='9fLYPigGHXkTyyQvU9zzoT3RTAXJ4dfHjbkg6ik2fHKKxjprSrh' #address to use for testing...

token_to_dispense = ['0fdb7ff8b37479b6eb7aab38d45af2cfeefabbefdc7eebc0348d25dd65bc2c91'] #the token you want to send. This is $lambo
token_amount = [1] #how many tokens will you send
erg_amount = 0.0001 #how much erg will you send to each address (in addition to tokens)

#no need to change anything below
submit = False
headers = {
    "accept": "application/json",
    "Content-Type": "application/json",
}
ergo = appkit.ErgoAppKit(node_url=node_url)
wallet_address = helper_functions.get_wallet_address(ergo=ergo, amount=1, wallet_mnemonic=wallet_mnemonic)[0]

#initializing lists
tokens_to_send = [token_amount]
erg_to_send = [erg_amount]
receiver_addresses = []
tokens = [token_to_dispense]
new_addresses = []

def check_address(address, tx_id, csv_filename):
    try:
        # Read data from CSV file
        with open(csv_filename, 'r') as file:
            csv_reader = csv.DictReader(file)
            csv_rows = list(csv_reader)
    except FileNotFoundError:
        print(f"Error: CSV file '{csv_filename}' not found.")
        return False

    # Check if both address and tx_id exist in the same row
    for row in csv_rows:
        if row.get('address') == address and row.get('tx_id') == tx_id:
            return True

    return False

def save_to_csv(address, csv_filename):
    # Check if the file exists
    file_exists = False
    try:
        with open(csv_filename, 'r') as file:
            file_exists = True
    except FileNotFoundError:
        pass

    # Open the CSV file in append mode
    with open(csv_filename, 'a', newline='') as file:
        fieldnames = list(address.keys())
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # Write header only if the file is created newly
        if not file_exists:
            writer.writeheader()

        # Write the dictionary to the CSV file
        writer.writerow(address)

def unconfirmed():
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    get_ergtree=(node_url+"/script/addressToTree/"+wallet_address)


    # get ergotree from address
    response = requests.get(get_ergtree)
    data = response.json()
    ergotree = data.get('tree')
    ergotree = ('"' + ergotree + '"')

    #get number of unconfirmed transactions for ergotree.
    get_unconfirmed = (node_url+"/transactions/unconfirmed/byErgoTree?limit=10&offset=0")
    response = requests.post(get_unconfirmed, data=ergotree , headers=headers)
    response_json = response.json()
    no_unconfirmed = len(response_json)

    return no_unconfirmed

#fetch last 20 transactions from address_to_monitor
while True:
    print(datetime.now())
    transactions = requests.post(node_url+"/blockchain/transaction/"+f"byAddress?offset=0&limit={no_transactions_to_fetch}", headers=headers, data=address_to_monitor)

    #print outputs that has the token
    addresses_with_amounts = []

    # Iterate through items and outputs
    for item in transactions.json()["items"]:
        for output in item["outputs"]:
            for asset in output["assets"]:
                # Check if the tokenId matches the specified value and the address doesn't start with "5vzu"
                if (
                        asset["tokenId"] in token_to_monitor
                        and output["address"].startswith("9")  and output["address"] not in blacklist #ignores contract addresses and blacklisted addresses
                ):
                    address = output["address"]
                    amount = asset["amount"]
                    tx_id = item["id"]
                    time = datetime.now()
                    addresses_with_amounts.append({"time": time,"address": address, "amount": amount,"tx_id":tx_id})
    # Print the result

    no_addresses = len(addresses_with_amounts)
    print ("Found", no_addresses, "addresses. Checking if txid has already been rewarded.....")
    if no_addresses > 0:
        for address in addresses_with_amounts:

            exists = check_address(address['address'],address['tx_id'], csv_filename)

            if exists is True:
                print(address['address'], "has already been rewarded for this transction (",address['tx_id'],")")
            sleep.sleep(0.1)

            if exists is False:
                print("New address found.",address['address'],"received", address["amount"],"in tx",address['tx_id'])
                sleep.sleep(0.1)
                new_addresses.append(address['address'])
                save_to_csv(address, csv_filename) # saves the addresses
                submit = True

        if submit is True: #if new txs found will assemble and send tokens

            print("Assembling TX.....")
            for address in new_addresses:
                if testing is True:
                    receiver_addresses.append(testing_address)
                elif testing is False:
                    receiver_addresses.append(address)
                tokens_to_send.append(token_amount)
                tokens.append(token_to_dispense)
                erg_to_send.append(erg_amount)

            no_unconfirmed = unconfirmed() # check if sender address has unconfirmed TXs.
            while no_unconfirmed > 0:
                no_unconfirmed = unconfirmed()
                print("Sender address has", no_unconfirmed,
                      "transaction(s). Waiting for all to be confirmed before processing next batch.")
                if no_unconfirmed == None:  # in case node can't be reached, try again until it get results.
                    no_unconfirmed = 1
                sleep.sleep(30)

            #if tx submit results in error, will retry until it submits.
            while True:
                try:
                    print("Sending Transaction")
                    txid= helper_functions.send_token(ergo=ergo, amount=erg_to_send, receiver_addresses=receiver_addresses, tokens=tokens, amount_tokens=tokens_to_send, wallet_mnemonic=wallet_mnemonic)

                    #txid="dummy"
                    print("TxID:", txid)
                    tx_submitted = {
                        "time": datetime.now(),
                        "address": receiver_addresses,
                        "txid": txid
                    }
                    break
                except Exception as e:
                    # Ignore any other exceptions and continue with the next iteration
                    print(f"Ignoring error: {e}")
            save_to_csv(tx_submitted,csv_tx_sent)
            #resetting lists
            tokens_to_send = [token_amount]
            erg_to_send = [erg_amount]
            receiver_addresses = []
            tokens = [token_to_dispense]
            new_addresses = []
            submit = False
    print("Sleeping for",check_interval,"seconds until next check...")
    sleep.sleep(check_interval)
