# this script will monitor an address outgoing transactions (sending)
#if the address sends a specific token (customizable) the script wil send those addresses a token of your choice!!
# ensure you have a file transactions.csv in the same folder as script.
#it needs the following headers, time, address, amount (all lower caps)
#rows can be empty
#Cobble together by Flying Pig to help distribute Comet in an "orderly" fashion
#---------USE AT YOUR OWN RISK-------------


import requests
import time as sleep
from datetime import datetime
from ergpy import helper_functions, appkit
import csv

node_url = "http://213.239.193.208:9053"
wallet_mnemonic = ""
address_to_monitor= "" #which address do you want to monitor
token_to_monitor = "" #token you want to monitor
no_transactions_to_fetch = 50 #fetches last x transactions from address to monitor.
check_interval = 120  #seconds between each check.

#TESTING Set to true if you want to test script. this will send any tokens to testing address instead of true recipient
#Use this to test your script. CSV FIle will still be populated with the actual recipients so if you want to send to these addresses once done testing, remove them first.
testing = True 
testing_address ='9fLYPigGHXkTyyQvU9zzoT3RTAXJ4dfHjbkg6ik2fHKKxjprSrh' #address to use for testing...

csv_filename = 'transactions.csv' # will save any matching addresses to this file and check any new addresses to ensure no one gets sent tokens twice!
token_to_dispense = ['0fdb7ff8b37479b6eb7aab38d45af2cfeefabbefdc7eebc0348d25dd65bc2c91'] #the token you want to send. This is $lambo
token_amount = [1] #how many tokens will you send to each recipient
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

def check_address(address, csv_filename):
    try:
        # Read data from CSV file
        with open(csv_filename  , 'r') as file:
            csv_reader = csv.DictReader(file)
            csv_addresses = set(row['address'] for row in csv_reader)
    except FileNotFoundError:
        print(f"Error: CSV file '{csv_filename}' not found.")
        return False

    # Check if the specified address matches with addresses in the CSV
    if address in csv_addresses:
        return True
    else:
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
                        asset["tokenId"] == token_to_monitor
                        and output["address"].startswith("9")#ignores contract addresses
                ):
                    address = output["address"]
                    amount = asset["amount"]
                    time = datetime.now()
                    addresses_with_amounts.append({"time": time,"address": address, "amount": amount})
    # Print the result

    no_addresses = len(addresses_with_amounts)
    print ("Found", no_addresses, "transactions. Checking if addresses have already been sent a reward....")
    if no_addresses > 0:
        for address in addresses_with_amounts:
            exists = check_address(address['address'],csv_filename)
            sleep.sleep(1)

            if exists is False:
                print("New TXs found",address['address'],"received", address["amount"])
                sleep.sleep(1)
                new_addresses.append(address['address'])
                save_to_csv(address, csv_filename) # saves the addresses
                submit = True
            print(new_addresses)

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

            print("Sending Transaction")
            print(helper_functions.send_token(ergo=ergo, amount=erg_to_send, receiver_addresses=receiver_addresses, tokens=tokens, amount_tokens=tokens_to_send, wallet_mnemonic=wallet_mnemonic))
            #print("New Addresses", receiver_addresses)
            #print("Tokens to send:", tokens)
            #print("Amount of tokens to send:", tokens_to_send)
            #print("Erg to send:", erg_to_send)

            #resetting lists
            tokens_to_send = [token_amount]
            erg_to_send = [erg_amount]
            receiver_addresses = []
            tokens = [token_to_dispense]
            new_addresses = []
            submit = False
    print("Sleeping for",check_interval,"seconds until next check...")
    sleep.sleep(check_interval)
