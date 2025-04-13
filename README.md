# Zora Trading Bot with Portia AI Integration

A trading bot designed to scan Zora Network's cryptocurrency market in real-time, identify high-performing coins, and provide buy/sell recommendations based on technical analysis and Portia AI's insights. Now with **real trading capabilities** using the Zora SDK!

## Features

- Direct integration with Zora Network via RPC API
- **NEW: Real trading capabilities via Zora SDK integration**
- **NEW: Support for both simulated and real trading modes**
- **NEW: Colorful CLI logging for improved monitoring**
- Optional integration with Zora GraphQL API when available
- Portia AI integration for enhanced analysis and trading recommendations
- Technical analysis using momentum, volume, and creator sentiment metrics
- Automated trading signals with confidence scoring
- Extensible strategy framework

## About Zora Network

Zora Network is an L2 (Layer 2) blockchain built on top of Ethereum using the OP stack. It enables:

- Creator economies with lower gas fees than the Ethereum mainnet
- Trading of social tokens and creator coins
- On-chain media NFTs and social content

## API Access

The bot uses Zora Network's RPC API for direct blockchain interaction:

1. **Public RPC Endpoint**:
   - The bot uses the public RPC URL: `https://rpc.zora.energy/`
   - This is rate-limited but sufficient for testing

2. **Enhanced API Access**:
   - For production use, get a non-rate-limited API key from [Conduit.xyz](https://conduit.xyz/)
   - This provides better performance for frequent API calls

3. **Optional GraphQL**:
   - The bot can also use a GraphQL endpoint if available for richer data queries

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Configure API keys:
   - Edit the `.env` file:
     ```
     # Zora Network API Configuration
     ZORA_RPC_URL=https://rpc.zora.energy/
     ZORA_API_KEY=your_conduit_api_key_here  # Get this from Conduit.xyz
     
     # Portia AI Configuration
     PORTIA_API_KEY=your_portia_api_key_here
     PORTIA_API_URL=https://api.portia.ai/v1
     
     # Optional GraphQL endpoint
     ZORA_GRAPHQL_URL=https://api.zora.co/graphql
     
     # Trading Configuration (for real trading)
     WALLET_PRIVATE_KEY=your_wallet_private_key_here
     ```

3. Run the bot:
   ```
   python run_bot.py
   ```

4. Demo the trading features:
   ```
   python real_trade_demo.py
   ```

## Configuration

Customize the bot's behavior by editing the `config.json` file:

```json
{
  "wallet_address": "0x53dae6e4b5009c1d5b64bee9cb42118914db7e66",
  "rpc_url": "https://rpc.zora.energy/",
  "chain_id": 8453,
  "api_key": "",
  "trading": {
    "auto_trade": true,
    "simulated": true,
    "strategy": "simple",
    "mock_capital": 5000.0,
    "max_trade_amount": 100.0,
    "confidence_threshold": 0.65,
    "slippage_tolerance": 0.01,
    "gas_limit_multiplier": 1.2
  },
  "security": {
    "private_key_env_var": "WALLET_PRIVATE_KEY",
    "enable_real_trades": false
  },
  "logging": {
    "level": "INFO",
    "log_file": "zora_bot.log",
    "colored_output": true
  }
}
```

## Trading Capabilities

The bot now includes comprehensive trading functionality:

1. **Zora SDK Integration**:
   - Execute real token swaps on the Zora Network
   - Support for token-to-token, ETH-to-token, and token-to-ETH swaps
   - Automatic token approval handling
   - Slippage protection and gas estimation

2. **Trading Modes**:
   - **Simulation Mode**: Test strategies with mock capital without executing real trades
   - **Real Trading**: Execute actual blockchain transactions (requires private key)

3. **Trading Agent Features**:
   - Process trading signals from multiple strategies
   - Configurable confidence thresholds
   - Flexible trade amount calculation
   - Comprehensive trade logging and history tracking

4. **Colorful CLI Interface**:
   - Color-coded log levels for better readability
   - Emoji icons for different operations (trades, WebSocket events, blockchain interactions)
   - Formatted tables for portfolio display

## Trading Strategies

The bot includes the following strategies:

1. **Momentum Strategy**: Identifies coins with strong directional movement using technical indicators like RSI, MACD, and volume analysis.

You can extend the bot with additional strategies by creating new classes that inherit from the `Strategy` base class in the `src/strategies` directory.

## Portia AI Integration

The bot leverages Portia AI for enhanced trading decisions:

- Sentiment analysis of coins and creators
- Growth potential assessment
- Risk scoring
- Market cycle identification
- Price prediction

## Project Structure

```
zora-portia-bot/
├── src/
│   ├── api/            # API clients
│   │   └── zora.py     # Zora Network API client
│   ├── models/         # Data models
│   │   ├── coin.py     # Token data model
│   │   ├── portfolio.py # Portfolio management
│   │   └── signal.py   # Trading signals
│   ├── strategies/     # Trading strategies
│   │   └── simple.py   # Simple trading strategy
│   ├── trading/        # Trading functionality
│   │   ├── agent.py    # Trading agent
│   │   └── zora_trader.py # Zora SDK trader implementation
│   ├── utils/          # Utility functions
│   ├── bot.py          # Main bot class
│   └── config.py       # Configuration handling
├── tests/              # Test directory
├── .env                # Environment variables
├── config.json         # Bot configuration
├── config.example.json # Example configuration
├── requirements.txt    # Dependencies
├── run_bot.py          # Entry point
├── real_trade_demo.py  # Demo of real trading capabilities
└── README.md           # Documentation
```

## Blockchain Interaction

The bot interacts with the Zora Network blockchain to:

1. **Get Coin Data**: 
   - Retrieve token metadata (name, symbol, decimals)
   - Get coin balances 
   - Fetch pricing from liquidity pools

2. **Analyze Trading Activity**:
   - Monitor transfer events for trading volume
   - Track holder counts and trading frequency
   - Analyze price movements over time

3. **Creator Economics**:
   - Evaluate creator reputation and activity
   - Monitor engagement metrics
   - Track creator reward distributions

## Running Tests

```
python -m unittest discover tests
```

## Future Enhancements

1. **Enhanced Trading Features**:
   - Advanced portfolio rebalancing
   - Dollar-cost averaging and scheduled buys
   - Stop-loss and take-profit orders
   - Gas optimization strategies

2. **Enhanced Analysis**:
   - Implement on-chain social sentiment analysis
   - Track cross-platform creator activity
   - Build predictive models for creator success

3. **User Interface**:
   - Add web dashboard for monitoring bot activity
   - Create mobile notifications for trading signals
   - Implement strategy backtesting UI

## License

[MIT License](LICENSE)
