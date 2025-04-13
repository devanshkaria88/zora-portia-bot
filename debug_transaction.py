#!/usr/bin/env python
"""
Transaction Debug Script

This script focuses specifically on testing transaction signing and execution
to help debug the "rawTransaction attribute missing" error.
"""
import os
import asyncio
import logging
import sys
import binascii
from web3 import Web3
from dotenv import load_dotenv
import colorama
from colorama import Fore, Style

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format=f"{Fore.GREEN}[%(asctime)s] %(levelname)s: %(message)s{Style.RESET_ALL}",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger()

# Load environment variables
load_dotenv()

# Constants
PRIVATE_KEY = os.environ.get("WALLET_PRIVATE_KEY")
WALLET_ADDRESS = "0x53dae6e4b5009c1d5b64bee9cb42118914db7e66"
ZORA_RPC = "https://rpc.zora.energy"

async def debug_transaction():
    """Test transaction signing and sending with different methods"""
    print("\n" + "="*80)
    print(f"{Fore.CYAN}TRANSACTION SIGNING DEBUG{Style.RESET_ALL}")
    print("="*80 + "\n")
    
    if not PRIVATE_KEY:
        logger.error("No private key found in environment variables")
        return
        
    # Clean private key (remove 0x if present)
    private_key = PRIVATE_KEY
    if private_key.startswith("0x"):
        private_key = private_key[2:]
        logger.info("Removed 0x prefix from private key")
    
    # Connect to Zora
    logger.info(f"Connecting to Zora Network: {ZORA_RPC}")
    w3 = Web3(Web3.HTTPProvider(ZORA_RPC))
    
    if not w3.is_connected():
        logger.error("Failed to connect to Zora Network")
        return
        
    logger.info(f"Connected to network with chain ID: {w3.eth.chain_id}")
    
    # Check wallet
    checksum_address = Web3.to_checksum_address(WALLET_ADDRESS)
    wei_balance = w3.eth.get_balance(checksum_address)
    eth_balance = w3.from_wei(wei_balance, 'ether')
    logger.info(f"Wallet balance: {eth_balance} ETH")
    
    # TEST 1: Simple ETH transfer
    logger.info("\n=== TEST 1: Simple ETH transfer ===")
    recipient = "0x0000000000000000000000000000000000000000"  # Burn address
    tiny_amount = w3.to_wei(0.00001, 'ether')  # Very tiny amount
    
    # Prepare transaction
    nonce = w3.eth.get_transaction_count(checksum_address)
    logger.info(f"Nonce: {nonce}")
    
    tx_params = {
        'nonce': nonce,
        'to': recipient,
        'value': tiny_amount,
        'gas': 21000,
        'gasPrice': w3.eth.gas_price,
        'chainId': w3.eth.chain_id,
    }
    
    logger.info(f"Transaction parameters: {tx_params}")
    
    # Try different signing methods
    logger.info("\nMethod 1: Using account.sign_transaction()")
    try:
        # Make sure private key starts with 0x
        if not private_key.startswith("0x"):
            signing_key = f"0x{private_key}"
        else:
            signing_key = private_key
            
        account = w3.eth.account.from_key(signing_key)
        logger.info(f"Account address from private key: {account.address}")
        
        # Verify account matches expected wallet
        if account.address.lower() != checksum_address.lower():
            logger.warning(f"⚠️ Account address ({account.address}) doesn't match expected wallet ({checksum_address})")
            user_continue = input("Continue anyway? (y/n): ")
            if user_continue.lower() != 'y':
                return
                
        # Sign the transaction with derived account
        signed_tx = w3.eth.account.sign_transaction(tx_params, signing_key)
        logger.info(f"Signed transaction hash: {signed_tx.hash.hex()}")
        
        # Check if it has rawTransaction
        if hasattr(signed_tx, 'rawTransaction'):
            logger.info(f"rawTransaction: {binascii.hexlify(signed_tx.rawTransaction)[:10]}...")
            
            # Ask user if they want to send the transaction
            user_send = input("\nDo you want to actually send this transaction? (y/n): ")
            if user_send.lower() == 'y':
                tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                logger.info(f"Transaction sent: {tx_hash.hex()}")
                logger.info(f"View on explorer: https://explorer.zora.energy/tx/{tx_hash.hex()}")
            else:
                logger.info("Transaction not sent (user choice)")
        else:
            logger.error("❌ rawTransaction attribute is missing!")
    except Exception as e:
        logger.error(f"Error in Method 1: {e}")
        
    # Method 2: Using EthAccount directly
    logger.info("\nMethod 2: Using eth_account.Account directly")
    try:
        from eth_account import Account
        Account.enable_unaudited_hdwallet_features()
        
        # Create account from private key
        account2 = Account.from_key(f"0x{private_key}" if not private_key.startswith("0x") else private_key)
        logger.info(f"Account created: {account2.address}")
        
        # Sign transaction
        tx_params2 = tx_params.copy()
        tx_params2['nonce'] = w3.eth.get_transaction_count(checksum_address)
        
        # Sign with this account
        signed_tx2 = account2.sign_transaction(tx_params2)
        logger.info(f"Signed transaction hash: {signed_tx2.hash.hex()}")
        
        # Check for rawTransaction
        if hasattr(signed_tx2, 'rawTransaction'):
            logger.info(f"rawTransaction: {binascii.hexlify(signed_tx2.rawTransaction)[:10]}...")
            
            # Ask user if they want to send
            user_send = input("\nDo you want to send this transaction using method 2? (y/n): ")
            if user_send.lower() == 'y':
                tx_hash = w3.eth.send_raw_transaction(signed_tx2.rawTransaction)
                logger.info(f"Transaction sent: {tx_hash.hex()}")
                logger.info(f"View on explorer: https://explorer.zora.energy/tx/{tx_hash.hex()}")
            else:
                logger.info("Transaction not sent (user choice)")
        else:
            logger.error("❌ rawTransaction attribute missing in method 2!")
    except Exception as e:
        logger.error(f"Error in Method 2: {e}")
    
    logger.info("\nDebug completed!")

if __name__ == "__main__":
    colorama.init(autoreset=True)
    asyncio.run(debug_transaction())
