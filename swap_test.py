#!/usr/bin/env python
"""
Direct Swap Test

This script attempts a direct swap on Zora Network using a fully manual approach
with standard web3.py methods to bypass the complex abstractions.
"""
import os
import sys
import json
import asyncio
import time
from hexbytes import HexBytes
from eth_account import Account
from web3 import Web3
from dotenv import load_dotenv
import colorama
from colorama import Fore, Style

# Load environment variables
load_dotenv()

# Configure nice colors
colorama.init(autoreset=True)

# Constants
PRIVATE_KEY = os.environ.get("WALLET_PRIVATE_KEY", "")
ZORA_RPC = "https://rpc.zora.energy"
# Fix the router address with proper checksum format
ROUTER_ADDRESS = "0x7De46C4087cF15Ac0FDac95441F151e1adDC9e00"  # Zora Exchange router
WETH_ADDRESS = "0x4200000000000000000000000000000000000006"  # WETH on Zora
TOKEN_ADDRESS = "0xe5B8A3ed37072683eB8D8E0C6D2B9c4A91807Bc9"  # "Vanela Gathiya" token

# Router ABI - just what we need
ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactETHForTokens",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "payable",
        "type": "function"
    }
]

def log_info(message):
    """Print info message with color"""
    print(f"{Fore.GREEN}[INFO] {message}{Style.RESET_ALL}")

def log_error(message):
    """Print error message with color"""
    print(f"{Fore.RED}[ERROR] {message}{Style.RESET_ALL}")

def log_warning(message):
    """Print warning message with color"""
    print(f"{Fore.YELLOW}[WARNING] {message}{Style.RESET_ALL}")

def log_success(message):
    """Print success message with color"""
    print(f"{Fore.CYAN}[SUCCESS] {message}{Style.RESET_ALL}")

async def main():
    """Main execution function"""
    print(f"\n{Fore.MAGENTA}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}DIRECT SWAP TEST ON ZORA NETWORK{Style.RESET_ALL}")
    print(f"{Fore.MAGENTA}{'=' * 80}{Style.RESET_ALL}\n")
    
    # Validate private key
    if not PRIVATE_KEY:
        log_error("No private key found in environment variables")
        return
    
    # Initialize web3
    log_info(f"Connecting to Zora Network: {ZORA_RPC}")
    w3 = Web3(Web3.HTTPProvider(ZORA_RPC))
    
    if not w3.is_connected():
        log_error("Failed to connect to network")
        return
    
    chain_id = w3.eth.chain_id
    log_info(f"Connected to Zora Network (Chain ID: {chain_id})")
    
    # Derive wallet address from private key
    try:
        account = Account.from_key(PRIVATE_KEY)
        wallet_address = account.address
        log_info(f"Using wallet: {wallet_address}")
    except Exception as e:
        log_error(f"Error deriving account from private key: {e}")
        return
        
    # Check wallet balance
    try:
        balance_wei = w3.eth.get_balance(wallet_address)
        balance_eth = w3.from_wei(balance_wei, 'ether')
        log_info(f"Wallet ETH balance: {balance_eth}")
        
        if balance_wei < w3.to_wei(0.0001, 'ether'):
            log_warning("Balance is very low for a swap transaction")
            proceed = input("Do you want to continue? (y/n): ")
            if proceed.lower() != 'y':
                log_info("Aborted by user")
                return
    except Exception as e:
        log_error(f"Error checking balance: {e}")
        return
    
    # Try a small swap
    try:
        # Prepare for swap
        log_info("Preparing swap transaction...")
        
        # Set up parameters
        # Convert addresses to proper checksum format
        weth_checksum = Web3.to_checksum_address(WETH_ADDRESS)
        token_checksum = Web3.to_checksum_address(TOKEN_ADDRESS)
        router_checksum = Web3.to_checksum_address(ROUTER_ADDRESS)
        
        log_info(f"Using router: {router_checksum}")
        log_info(f"WETH address: {weth_checksum}")
        log_info(f"Token address: {token_checksum}")
        
        path = [weth_checksum, token_checksum]  # Swap path: ETH -> WETH -> TOKEN
        amount_in_wei = w3.to_wei(0.0001, 'ether')  # Very small amount (0.0001 ETH)
        min_tokens_out = 1  # Just 1 token unit as minimum
        deadline = int(time.time() + 60 * 20)  # 20 minutes from now
        
        # Set up router contract
        router = w3.eth.contract(address=router_checksum, abi=ROUTER_ABI)
        
        # Try different transaction construction method
        tx = {
            'from': wallet_address,
            'value': amount_in_wei,
            'gas': 200000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(wallet_address),
            'chainId': chain_id,
            'to': router_checksum
        }
        
        # Encode function call properly
        func_obj = router.functions.swapExactETHForTokens(
            min_tokens_out,
            path,
            wallet_address,
            deadline
        )
        tx_data = func_obj.build_transaction({
            'from': wallet_address,
            'value': amount_in_wei,
            'gas': 200000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(wallet_address),
            'chainId': chain_id,
        })
        
        # Get just the data field from the built transaction
        tx['data'] = tx_data['data']
        
        log_info(f"Transaction prepared with nonce {tx['nonce']}")
        log_info(f"Gas price: {w3.from_wei(w3.eth.gas_price, 'gwei')} gwei")
        
        # Try to estimate gas
        try:
            estimated_gas = w3.eth.estimate_gas(tx)
            tx['gas'] = int(estimated_gas * 1.2)  # Add 20% buffer
            log_info(f"Estimated gas: {estimated_gas}, using {tx['gas']}")
        except Exception as e:
            log_warning(f"Could not estimate gas: {e}")
        
        # Sign transaction
        log_info("Signing transaction...")
        try:
            signed = Account.sign_transaction(tx, PRIVATE_KEY)
            
            # Check if signed transaction has raw_transaction (with underscore!)
            if hasattr(signed, 'raw_transaction'):
                log_success("Transaction signed successfully!")
                
                # Ask for confirmation
                confirm = input(f"Send transaction to swap {w3.from_wei(amount_in_wei, 'ether')} ETH? (y/n): ")
                if confirm.lower() != 'y':
                    log_info("Transaction canceled by user")
                    return
                
                # Send transaction
                tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
                log_success(f"Transaction sent! Hash: {tx_hash.hex()}")
                log_info(f"View on explorer: https://explorer.zora.energy/tx/{tx_hash.hex()}")
                
                # Wait for receipt
                log_info("Waiting for transaction receipt...")
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
                
                if receipt.status == 1:
                    log_success("Transaction successful!")
                    log_info(f"Gas used: {receipt.gasUsed}")
                else:
                    log_error("Transaction failed on-chain!")
            else:
                log_error("Signed transaction missing raw_transaction attribute")
                # Try to debug the signed transaction
                log_info(f"Signed transaction attributes: {dir(signed)}")
        except Exception as e:
            log_error(f"Error signing or sending transaction: {e}")
            
    except Exception as e:
        log_error(f"Error in swap process: {e}")
    
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScript interrupted by user")
    except Exception as e:
        log_error(f"Unexpected error: {e}")
