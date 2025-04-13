"""
Zora SDK Trading Integration

This module provides trading functionality using Zora's SDK for actual token swaps.
It integrates with Zora's exchange contracts to perform trades on the Zora Network.
"""
import os
import json
import logging
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from decimal import Decimal
from web3 import Web3
from web3.exceptions import TransactionNotFound
from eth_typing import ChecksumAddress

from ..api.zora import ZoraClient
from ..models.coin import Coin
from ..models.signal import Signal, SignalType

logger = logging.getLogger(__name__)

# Constants
WETH_ADDRESS = "0x4200000000000000000000000000000000000006"  # WETH on Zora Network
ROUTER_ADDRESS = "0x7De46C4087cF15Ac0FDac95441F151e1adDC9e00"  # Zora Exchange router
FACTORY_ADDRESS = "0x98570416DC69396e906e75FD59e7c7D67ECaE4E2"  # Zora Exchange factory

# Define the Router ABI (partial, with just the methods we need)
ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForETH",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
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
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"}
        ],
        "name": "getAmountsOut",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# ERC20 approval function signature
ERC20_APPROVE_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

class ZoraSDKTrader:
    """
    Handles actual token trading on the Zora Network using their SDK
    """
    
    def __init__(
        self, 
        zora_client: ZoraClient, 
        wallet_address: str, 
        private_key: Optional[str] = None,
        slippage_tolerance: float = 0.01,  # 1% slippage tolerance by default
        gas_limit_multiplier: float = 1.2,  # Add 20% to estimated gas by default
        deadline_minutes: int = 20  # Transaction deadline in minutes
    ):
        self.zora_client = zora_client
        self.wallet_address = Web3.to_checksum_address(wallet_address)
        self.private_key = private_key or os.environ.get("WALLET_PRIVATE_KEY")
        
        # Configuration parameters
        self.slippage_tolerance = slippage_tolerance
        self.gas_limit_multiplier = gas_limit_multiplier
        self.deadline_minutes = deadline_minutes
        
        # Initialize web3 from the ZoraClient
        self.w3 = zora_client.w3
        
        # Initialize the router contract
        self.router = self.w3.eth.contract(
            address=Web3.to_checksum_address(ROUTER_ADDRESS),
            abi=ROUTER_ABI
        )
    
    async def get_token_contract(self, token_address: str):
        """
        Get the contract instance for an ERC20 token
        
        Args:
            token_address: The token contract address
            
        Returns:
            Web3 contract instance
        """
        token_address = Web3.to_checksum_address(token_address)
        return self.w3.eth.contract(
            address=token_address,
            abi=self.zora_client.ERC20_ABI
        )
    
    async def get_token_allowance(self, token_address: str, spender_address: str = ROUTER_ADDRESS) -> int:
        """
        Check the token allowance for the router contract
        
        Args:
            token_address: The token contract address
            spender_address: The address allowed to spend tokens (default: router)
            
        Returns:
            Current allowance amount
        """
        try:
            token_address = Web3.to_checksum_address(token_address)
            spender_address = Web3.to_checksum_address(spender_address)
            
            token_contract = await self.get_token_contract(token_address)
            allowance = token_contract.functions.allowance(
                self.wallet_address, 
                spender_address
            ).call()
            
            return allowance
        except Exception as e:
            logger.error(f"❌ Failed to check token allowance: {e}")
            return 0
            
    async def approve_token_spending(self, token_address: str, amount: int = 2**256 - 1) -> Optional[str]:
        """
        Approve the router contract to spend tokens
        
        Args:
            token_address: The token contract address
            amount: The amount to approve (default: unlimited)
            
        Returns:
            Transaction hash if successful, None otherwise
        """
        if not self.private_key:
            logger.error("❌ Cannot approve token spending: Private key not provided")
            return None
            
        try:
            token_address = Web3.to_checksum_address(token_address)
            token_contract = await self.get_token_contract(token_address)
            
            # Check current allowance first
            current_allowance = await self.get_token_allowance(token_address)
            if current_allowance >= amount:
                logger.info(f"✅ Token {token_address} already approved for spending")
                return "Already Approved"
                
            # Prepare approval transaction
            nonce = self.w3.eth.get_transaction_count(self.wallet_address)
            
            # Build approve transaction
            approve_tx = token_contract.functions.approve(
                Web3.to_checksum_address(ROUTER_ADDRESS),
                amount
            ).build_transaction({
                'from': self.wallet_address,
                'gas': 100000,  # Standard gas limit for approvals
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce,
            })
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(approve_tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for transaction receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt.status == 1:
                logger.info(f"✅ Token {token_address} approved for spending. Transaction: {tx_hash.hex()}")
                return tx_hash.hex()
            else:
                logger.error(f"❌ Token approval failed. Transaction: {tx_hash.hex()}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to approve token spending: {e}")
            return None
    
    async def get_quote(self, token_in: str, token_out: str, amount_in: int) -> Tuple[float, List[int]]:
        """
        Get a quote for swapping tokens
        
        Args:
            token_in: Address of the input token
            token_out: Address of the output token
            amount_in: Amount of input tokens (in wei)
            
        Returns:
            Tuple of (price quote, amounts list)
        """
        try:
            # Prepare the path for the swap
            path = [Web3.to_checksum_address(token_in), Web3.to_checksum_address(token_out)]
            
            # Get the amounts out
            amounts = self.router.functions.getAmountsOut(amount_in, path).call()
            
            # Calculate the price
            price = amounts[1] / amounts[0]
            
            return price, amounts
        except Exception as e:
            logger.error(f"❌ Failed to get swap quote: {e}")
            return 0, [0, 0]
    
    def _calculate_min_amount_out(self, amount_out: int) -> int:
        """
        Calculate minimum output amount with slippage tolerance
        
        Args:
            amount_out: Expected output amount
            
        Returns:
            Minimum acceptable output amount
        """
        return int(amount_out * (1 - self.slippage_tolerance))
    
    def _get_deadline(self) -> int:
        """
        Calculate the transaction deadline timestamp
        
        Returns:
            Unix timestamp for the deadline
        """
        return int(time.time()) + (self.deadline_minutes * 60)
    
    async def execute_swap(
        self, 
        token_in: str, 
        token_out: str, 
        amount_in: Union[int, float, Decimal],
        min_amount_out: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a token swap on Zora Network
        
        Args:
            token_in: Address of the input token
            token_out: Address of the output token
            amount_in: Amount of input tokens (in decimals)
            min_amount_out: Minimum acceptable output amount (with slippage)
            
        Returns:
            Dictionary with swap results if successful, None otherwise
        """
        if not self.private_key:
            logger.error("❌ Cannot execute swap: Private key not provided")
            return None
            
        try:
            # Convert addresses to checksummed format
            token_in = Web3.to_checksum_address(token_in)
            token_out = Web3.to_checksum_address(token_out)
            
            # Get token decimal information for precise calculations
            token_in_contract = await self.get_token_contract(token_in)
            token_in_decimals = token_in_contract.functions.decimals().call()
            
            # Convert amount to wei based on token decimals
            if isinstance(amount_in, (float, Decimal)):
                amount_in_wei = int(amount_in * (10 ** token_in_decimals))
            else:
                amount_in_wei = amount_in
                
            # Get the swap quote
            _, amounts = await self.get_quote(token_in, token_out, amount_in_wei)
            
            # If no minimum amount provided, calculate based on slippage
            if min_amount_out is None and len(amounts) > 1:
                min_amount_out = self._calculate_min_amount_out(amounts[1])
            
            # Make sure we have allowance for this token
            await self.approve_token_spending(token_in)
                
            # Prepare the path for the swap
            path = [token_in, token_out]
            
            # Get the deadline timestamp
            deadline = self._get_deadline()
            
            # Prepare the swap transaction
            nonce = self.w3.eth.get_transaction_count(self.wallet_address)
            
            # Build the swap transaction
            swap_tx = self.router.functions.swapExactTokensForTokens(
                amount_in_wei,
                min_amount_out,
                path,
                self.wallet_address,
                deadline
            ).build_transaction({
                'from': self.wallet_address,
                'gas': 300000,  # We'll estimate this properly
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce,
            })
            
            # Try to estimate gas
            try:
                estimated_gas = self.w3.eth.estimate_gas(swap_tx)
                swap_tx['gas'] = int(estimated_gas * self.gas_limit_multiplier)
            except Exception as e:
                logger.warning(f"⚠️ Could not estimate gas: {e}. Using default gas limit.")
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(swap_tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            logger.info(f"🔄 Swap transaction sent: {tx_hash.hex()}")
            
            # Wait for transaction receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            if receipt.status == 1:
                logger.info(f"✅ Swap successful! Transaction: {tx_hash.hex()}")
                
                # Try to determine the exact amount out from the transaction logs
                amount_out = 0
                # This would require parsing the event logs which is more complex
                # For now, we'll use the quoted amount
                if len(amounts) > 1:
                    amount_out = amounts[1]
                
                # Return the swap details
                return {
                    "success": True,
                    "transaction_hash": tx_hash.hex(),
                    "token_in": token_in,
                    "token_out": token_out,
                    "amount_in": amount_in_wei,
                    "amount_out": amount_out,
                    "gas_used": receipt.gasUsed,
                    "effective_gas_price": receipt.effectiveGasPrice if hasattr(receipt, 'effectiveGasPrice') else 0,
                    "block_number": receipt.blockNumber
                }
            else:
                logger.error(f"❌ Swap failed. Transaction: {tx_hash.hex()}")
                return {
                    "success": False,
                    "transaction_hash": tx_hash.hex(),
                    "error": "Transaction failed"
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to execute swap: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def swap_eth_for_tokens(
        self, 
        token_out: str, 
        eth_amount: Union[int, float, Decimal],
        min_tokens_out: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Swap ETH for tokens
        
        Args:
            token_out: Address of the output token
            eth_amount: Amount of ETH to swap (in ETH, not wei)
            min_tokens_out: Minimum acceptable output amount (with slippage)
            
        Returns:
            Dictionary with swap results if successful, None otherwise
        """
        try:
            # Convert ETH amount to Wei
            eth_amount_wei = self.zora_client.w3.to_wei(eth_amount, 'ether')
            
            # Get the path for the swap (ETH -> WETH -> Token)
            # Ensure proper checksum formatting for all addresses
            weth_address = Web3.to_checksum_address(WETH_ADDRESS)
            token_out_address = Web3.to_checksum_address(token_out)
            wallet_address = Web3.to_checksum_address(self.wallet_address)
            router_address = Web3.to_checksum_address(ROUTER_ADDRESS)
            
            path = [weth_address, token_out_address]
            
            # Get a quote if available
            try:
                quote, amounts = await self.get_quote(WETH_ADDRESS, token_out, eth_amount_wei)
                logger.info(f"💰 Got quote for {eth_amount} ETH to token: {amounts[-1]} tokens")
                
                # Use the quoted amount with slippage
                expected_out = amounts[-1]
                min_out = min_tokens_out or self._calculate_min_amount_out(expected_out)
                
            except Exception as e:
                logger.error(f"❌ Failed to get swap quote: {e}")
                if not min_tokens_out:
                    # Set a minimal minimum amount if quote fails
                    min_out = 1
                    logger.warning(f"⚠️ Setting minimum output to 1 token unit")
                else:
                    min_out = min_tokens_out
            
            # Setup the transaction
            router = self.zora_client.w3.eth.contract(
                address=router_address,
                abi=ROUTER_ABI
            )
            
            deadline = self._get_deadline()
            
            # Fix private key format - remove '0x' prefix if present
            cleaned_private_key = self.private_key
            if cleaned_private_key.startswith('0x'):
                cleaned_private_key = cleaned_private_key[2:]
                logger.debug(f"Removed 0x prefix from private key")
            
            # Prepare the function call
            func_obj = router.functions.swapExactETHForTokens(
                min_out,  # Min tokens out (with slippage)
                path,  # Path of the swap
                wallet_address,  # Recipient 
                deadline  # Deadline timestamp
            )
            
            # Build transaction with all parameters
            tx_params = {
                'from': wallet_address,
                'value': eth_amount_wei,
                'nonce': self.zora_client.w3.eth.get_transaction_count(wallet_address),
                'gasPrice': self.zora_client.w3.eth.gas_price,
                'gas': 300000,  # Starting estimate
                'chainId': self.zora_client.w3.eth.chain_id
            }
            
            # Build the transaction
            tx = func_obj.build_transaction(tx_params)
            
            # Estimate gas if possible
            try:
                estimated_gas = self.zora_client.w3.eth.estimate_gas(tx)
                tx['gas'] = int(estimated_gas * self.gas_limit_multiplier)
                logger.info(f"⛽ Estimated gas: {estimated_gas}, using: {tx['gas']}")
            except Exception as e:
                logger.warning(f"⚠️ Could not estimate gas: {e}. Using default gas limit.")
            
            # Sign the transaction
            if not cleaned_private_key:
                return {
                    "success": False,
                    "error": "Private key not provided, cannot execute real transaction"
                }
            
            try:
                # Sign with the appropriate private key format
                pk_for_signing = f"0x{cleaned_private_key}" if not cleaned_private_key.startswith('0x') else cleaned_private_key
                
                # Sign the transaction
                signed_tx = self.zora_client.w3.eth.account.sign_transaction(tx, pk_for_signing)
                
                # Send the transaction - using raw_transaction (with underscore) not rawTransaction
                tx_hash = self.zora_client.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                logger.info(f"📤 Transaction sent: {tx_hash.hex()}")
                
                # Return success information
                return {
                    "success": True,
                    "transaction_hash": tx_hash.hex(),
                    "eth_amount": eth_amount,
                    "min_tokens_out": min_out
                }
            except Exception as tx_error:
                logger.error(f"❌ Transaction signing/sending error: {tx_error}")
                return {
                    "success": False,
                    "error": f"Transaction signing/sending error: {tx_error}"
                }
            
        except Exception as e:
            logger.error(f"❌ Failed to execute ETH swap: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def swap_tokens_for_eth(
        self, 
        token_in: str, 
        token_amount: Union[int, float, Decimal],
        min_eth_out: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Swap tokens for ETH
        
        Args:
            token_in: Address of the input token
            token_amount: Amount of tokens to swap (in token units, not wei)
            min_eth_out: Minimum acceptable ETH output (with slippage)
            
        Returns:
            Dictionary with swap results if successful, None otherwise
        """
        if not self.private_key:
            logger.error("❌ Cannot execute swap: Private key not provided")
            return None
            
        try:
            # Convert addresses to checksummed format
            token_in = Web3.to_checksum_address(token_in)
            
            # Get token decimal information for precise calculations
            token_in_contract = await self.get_token_contract(token_in)
            token_in_decimals = token_in_contract.functions.decimals().call()
            
            # Convert amount to wei based on token decimals
            if isinstance(token_amount, (float, Decimal)):
                token_amount_wei = int(token_amount * (10 ** token_in_decimals))
            else:
                token_amount_wei = token_amount
                
            # Make sure we have allowance for this token
            await self.approve_token_spending(token_in)
            
            # Get the swap quote
            _, amounts = await self.get_quote(token_in, WETH_ADDRESS, token_amount_wei)
            
            # If no minimum amount provided, calculate based on slippage
            if min_eth_out is None and len(amounts) > 1:
                min_eth_out = self._calculate_min_amount_out(amounts[1])
            
            # Prepare the path for the swap
            path = [token_in, WETH_ADDRESS]
            
            # Get the deadline timestamp
            deadline = self._get_deadline()
            
            # Prepare the swap transaction
            nonce = self.w3.eth.get_transaction_count(self.wallet_address)
            
            # Build the swap transaction
            swap_tx = self.router.functions.swapExactTokensForETH(
                token_amount_wei,
                min_eth_out,
                path,
                self.wallet_address,
                deadline
            ).build_transaction({
                'from': self.wallet_address,
                'gas': 300000,  # We'll estimate this properly
                'gasPrice': self.w3.eth.gas_price,
                'nonce': nonce,
            })
            
            # Try to estimate gas
            try:
                estimated_gas = self.w3.eth.estimate_gas(swap_tx)
                swap_tx['gas'] = int(estimated_gas * self.gas_limit_multiplier)
            except Exception as e:
                logger.warning(f"⚠️ Could not estimate gas: {e}. Using default gas limit.")
            
            # Sign and send transaction
            signed_tx = self.w3.eth.account.sign_transaction(swap_tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            logger.info(f"🔄 Token-to-ETH swap transaction sent: {tx_hash.hex()}")
            
            # Wait for transaction receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            if receipt.status == 1:
                logger.info(f"✅ Token-to-ETH swap successful! Transaction: {tx_hash.hex()}")
                
                # Return the swap details
                return {
                    "success": True,
                    "transaction_hash": tx_hash.hex(),
                    "token_in": token_in,
                    "token_out": "ETH",
                    "amount_in": token_amount_wei,
                    "amount_out": amounts[1] if len(amounts) > 1 else 0,
                    "gas_used": receipt.gasUsed,
                    "effective_gas_price": receipt.effectiveGasPrice if hasattr(receipt, 'effectiveGasPrice') else 0,
                    "block_number": receipt.blockNumber
                }
            else:
                logger.error(f"❌ Token-to-ETH swap failed. Transaction: {tx_hash.hex()}")
                return {
                    "success": False,
                    "transaction_hash": tx_hash.hex(),
                    "error": "Transaction failed"
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to execute token-to-ETH swap: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def process_trade_signal(self, signal: Signal, amount_usd: float) -> Dict[str, Any]:
        """
        Process a trade signal by executing the appropriate swap
        
        Args:
            signal: The trade signal object
            amount_usd: Amount in USD to trade
            
        Returns:
            Dictionary with trade results
        """
        try:
            coin = signal.coin
            
            if signal.type == SignalType.BUY:
                # Buying: we're swapping ETH for tokens
                
                # Calculate ETH amount based on USD value and ETH price
                eth_price = await self.zora_client.get_eth_price()
                if not eth_price or eth_price <= 0:
                    return {
                        "success": False,
                        "error": "Could not determine ETH price"
                    }
                    
                eth_amount = amount_usd / eth_price
                
                # Execute the swap
                result = await self.swap_eth_for_tokens(
                    token_out=coin.address,
                    eth_amount=eth_amount
                )
                
                if result and result.get("success"):
                    return {
                        "success": True,
                        "type": "BUY",
                        "coin": coin,
                        "amount_usd": amount_usd,
                        "eth_amount": eth_amount,
                        "transaction_hash": result.get("transaction_hash")
                    }
                else:
                    return {
                        "success": False,
                        "type": "BUY",
                        "coin": coin,
                        "error": result.get("error") if result else "Unknown error"
                    }
                    
            elif signal.type == SignalType.SELL:
                # Selling: we're swapping tokens for ETH
                
                # Determine token amount based on USD value
                if not coin.current_price or coin.current_price <= 0:
                    return {
                        "success": False,
                        "error": "Could not determine token price"
                    }
                    
                token_amount = amount_usd / coin.current_price
                
                # Execute the swap
                result = await self.swap_tokens_for_eth(
                    token_in=coin.address,
                    token_amount=token_amount
                )
                
                if result and result.get("success"):
                    return {
                        "success": True,
                        "type": "SELL",
                        "coin": coin,
                        "amount_usd": amount_usd,
                        "token_amount": token_amount,
                        "transaction_hash": result.get("transaction_hash")
                    }
                else:
                    return {
                        "success": False,
                        "type": "SELL",
                        "coin": coin,
                        "error": result.get("error") if result else "Unknown error"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Unsupported signal type: {signal.type}"
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to process trade signal: {e}")
            return {
                "success": False,
                "error": str(e)
            }
