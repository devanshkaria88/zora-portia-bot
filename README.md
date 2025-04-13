# Zora Trading Bot with Portia AI Integration

A trading bot designed to scan Zora Network's cryptocurrency market in real-time, identify high-performing coins, and provide buy/sell recommendations based on technical analysis and Portia AI's insights.

## Features

- Direct integration with Zora Network via RPC API
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
     ```

3. Run the bot:
   ```
   python run_bot.py
   ```

## Configuration

Customize the bot's behavior by editing the `config.json` file:

```json
{
  "zora": {
    "rpc_url": "https://rpc.zora.energy/",
    "graphql_url": "https://api.zora.co/graphql"
  },
  "portia": {
    "api_url": "https://api.portia.ai/v1"
  },
  "max_coins": 50,
  "coins_list_limit": 100,
  "scan_interval": 120,
  "fetch_metadata": true,
  "fetch_trades": true,
  "trades_limit": 20,
  "max_signals_per_run": 5,
  "min_signal_strength": 0.7,
  "strategies": {
    "momentum": {
      "enabled": true,
      "rsi_period": 14,
      "rsi_overbought": 70,
      "rsi_oversold": 30,
      "macd_fast": 12,
      "macd_slow": 26,
      "macd_signal": 9,
      "volume_threshold": 2.5
    }
  }
}
```

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
│   ├── models/         # Data models
│   ├── strategies/     # Trading strategies
│   ├── utils/          # Utility functions
│   ├── bot.py          # Main bot class
│   └── config.py       # Configuration handling
├── tests/              # Test directory
├── .env                # Environment variables
├── config.json         # Bot configuration
├── requirements.txt    # Dependencies
├── run_bot.py          # Entry point
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

1. **Trading Integration**:
   - Connect to DEXs on Zora Network for actual trading
   - Implement wallet integration for transaction signing
   - Add position management and portfolio tracking

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
