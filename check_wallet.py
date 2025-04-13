#!/usr/bin/env python
"""
Multi-Network Wallet Balance Checker

This script checks a wallet's balance across multiple networks (ETH, Base, Zora)
and displays all token balances to help troubleshoot trading issues.
"""
import os
import asyncio
import json
import logging
from web3 import Web3
from dotenv import load_dotenv
import colorama
from colorama import Fore, Style
import requests

# Load environment variables
load_dotenv()

# Configuration
WALLET_ADDRESS = Web3.to_checksum_address("0x53dae6e4b5009c1d5b64bee9cb42118914db7e66")
PRIVATE_KEY = os.environ.get("WALLET_PRIVATE_KEY")

# RPC URLs
ETHEREUM_RPC = "https://mainnet.infura.io/v3/9aa3d95b3bc440fa88ea12eaa4456161"  # Public Infura endpoint
BASE_RPC = "https://mainnet.base.org"
ZORA_RPC = "https://rpc.zora.energy"

# Chain IDs
ETHEREUM_CHAIN_ID = 1
BASE_CHAIN_ID = 8453
ZORA_CHAIN_ID = 7777777

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format=f"{Fore.GREEN}%(asctime)s{Style.RESET_ALL} [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("wallet_checker")

async def check_eth_balance(web3, address, network_name):
    """Check ETH balance on the specified network"""
    try:
        wei_balance = web3.eth.get_balance(address)
        eth_balance = web3.from_wei(wei_balance, 'ether')
        logger.info(f"{network_name} ETH Balance: {Fore.CYAN}{eth_balance:.6f} ETH{Style.RESET_ALL}")
        
        # Estimate USD value
        eth_price = await get_eth_price()
        if eth_price:
            usd_value = float(eth_balance) * eth_price
            logger.info(f"{network_name} USD Value: {Fore.GREEN}${usd_value:.2f}{Style.RESET_ALL}")
        
        return float(eth_balance)
    except Exception as e:
        logger.error(f"Error checking {network_name} balance: {e}")
        return 0

async def get_token_balance(web3, token_address, wallet_address, network_name):
    """Get balance of a specific token"""
    token_abi = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "symbol",
            "outputs": [{"name": "", "type": "string"}],
            "type": "function"
        },
        {
            "constant": True,
            "inputs": [],
            "name": "name",
            "outputs": [{"name": "", "type": "string"}],
            "type": "function"
        }
    ]
    
    try:
        token_contract = web3.eth.contract(address=token_address, abi=token_abi)
        
        # Get token details
        try:
            symbol = token_contract.functions.symbol().call()
        except:
            symbol = "???"
            
        try:
            name = token_contract.functions.name().call()
        except:
            name = "Unknown Token"
            
        try:
            decimals = token_contract.functions.decimals().call()
        except:
            decimals = 18
            
        # Get balance
        raw_balance = token_contract.functions.balanceOf(wallet_address).call()
        balance = raw_balance / (10 ** decimals)
        
        if balance > 0:
            logger.info(f"{network_name} Token: {Fore.YELLOW}{symbol}{Style.RESET_ALL} ({name}): {Fore.CYAN}{balance:.6f}{Style.RESET_ALL}")
            return {
                "symbol": symbol,
                "name": name,
                "balance": balance,
                "address": token_address
            }
        return None
    except Exception as e:
        logger.error(f"Error checking token {token_address} on {network_name}: {e}")
        return None

async def get_eth_price():
    """Get ETH price from CoinGecko"""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return data.get("ethereum", {}).get("usd", 0)
        return 0
    except Exception as e:
        logger.error(f"Error fetching ETH price: {e}")
        return 0

async def fetch_tokens_from_etherscan(address, network):
    """Fetch token balances from Etherscan/Basescan API"""
    api_keys = {
        "ethereum": os.environ.get("ETHERSCAN_API_KEY", "YourApiKeyToken"),
        "base": os.environ.get("BASESCAN_API_KEY", "YourApiKeyToken")
    }
    
    api_key = api_keys.get(network, "YourApiKeyToken")
    
    if network == "ethereum":
        base_url = "https://api.etherscan.io/api"
    elif network == "base":
        base_url = "https://api.basescan.org/api"
    else:
        return []
    
    url = f"{base_url}?module=account&action=tokenlist&address={address}&apikey={api_key}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "1":
                return data.get("result", [])
            else:
                logger.warning(f"API returned status {data.get('status')}: {data.get('message')}")
                return []
        else:
            logger.error(f"Error fetching tokens from {network}scan: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Exception fetching tokens from {network}scan: {e}")
        return []

async def check_network(web3, network_name, chain_id):
    """Check wallet balance on a specific network"""
    print(f"\n{Fore.BLUE}{'=' * 40}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}CHECKING {network_name.upper()} NETWORK (Chain ID: {chain_id}){Style.RESET_ALL}")
    print(f"{Fore.BLUE}{'=' * 40}{Style.RESET_ALL}\n")
    
    # Check if we can connect to the network
    try:
        block_number = web3.eth.block_number
        logger.info(f"Connected to {network_name}, current block: {block_number}")
    except Exception as e:
        logger.error(f"Cannot connect to {network_name}: {e}")
        return
    
    # Check native token balance
    eth_balance = await check_eth_balance(web3, WALLET_ADDRESS, network_name)
    
    # Check common tokens
    weth_address = {
        ETHEREUM_CHAIN_ID: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        BASE_CHAIN_ID: "0x4200000000000000000000000000000000000006",
        ZORA_CHAIN_ID: "0x4200000000000000000000000000000000000006"
    }.get(chain_id)
    
    usdc_address = {
        ETHEREUM_CHAIN_ID: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        BASE_CHAIN_ID: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        ZORA_CHAIN_ID: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    }.get(chain_id)
    
    if weth_address:
        await get_token_balance(web3, Web3.to_checksum_address(weth_address), WALLET_ADDRESS, network_name)
    
    if usdc_address:
        await get_token_balance(web3, Web3.to_checksum_address(usdc_address), WALLET_ADDRESS, network_name)
    
    # Etherscan API check
    if network_name.lower() in ["ethereum", "base"]:
        logger.info(f"Checking {network_name}scan API for token balances...")
        tokens = await fetch_tokens_from_etherscan(WALLET_ADDRESS, network_name.lower())
        if tokens:
            for token in tokens:
                if float(token.get("balance", 0)) > 0:
                    token_address = Web3.to_checksum_address(token.get("contractAddress"))
                    await get_token_balance(web3, token_address, WALLET_ADDRESS, network_name)
        else:
            logger.info(f"No additional tokens found through {network_name}scan API")

async def main():
    """Check wallet balance across multiple networks"""
    colorama.init(autoreset=True)
    
    print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}WALLET BALANCE CHECKER{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}")
    
    logger.info(f"Checking balances for wallet: {WALLET_ADDRESS}")
    
    # Initialize Web3 providers
    eth_web3 = Web3(Web3.HTTPProvider(ETHEREUM_RPC))
    base_web3 = Web3(Web3.HTTPProvider(BASE_RPC))
    zora_web3 = Web3(Web3.HTTPProvider(ZORA_RPC))
    
    # Check Ethereum Mainnet
    await check_network(eth_web3, "Ethereum", ETHEREUM_CHAIN_ID)
    
    # Check Base Network
    await check_network(base_web3, "Base", BASE_CHAIN_ID)
    
    # Check Zora Network
    await check_network(zora_web3, "Zora", ZORA_CHAIN_ID)
    
    print(f"\n{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}BALANCE CHECK COMPLETE{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'=' * 60}{Style.RESET_ALL}")

if __name__ == "__main__":
    asyncio.run(main())
