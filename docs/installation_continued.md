# Installation and Getting Started (Continued)

## Common First-Run Issues (Continued)

### API Rate Limiting

If you encounter rate limit errors:

```
WARNING:src.api.zora:Rate limited by Zora SDK API. Retrying in 2.0 seconds...
```

**Solution**: Increase the `scan_interval` in your config.json file to reduce the frequency of API calls. Consider obtaining an API key for higher rate limits.

### Python Dependencies

If you see errors about missing modules:

```
ModuleNotFoundError: No module named 'aiohttp'
```

**Solution**: Ensure you've activated your virtual environment and installed all dependencies:

```bash
# Activate the virtual environment (if not already activated)
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Invalid Wallet Address

If you see errors about an invalid wallet address:

```
ERROR:src.trading.agent:Invalid wallet address format: 0xInvalidAddress
```

**Solution**: Ensure you're using a valid Ethereum wallet address in the correct format (0x followed by 40 hexadecimal characters).

## Running in Auto-Trading Mode

Once you've confirmed the bot is working in simulation mode, you can enable auto-trading (still with simulated trades):

```bash
python run_bot.py --wallet YOUR_WALLET_ADDRESS --auto-trade --mock-capital 5000
```

This starts the bot with automatic trading using $5000 of mock capital.

### Auto-Trading Output

With auto-trading enabled, you'll see additional output about trade execution:

```
INFO:src.bot:🤖 Starting automated trading loop
INFO:src.trading.agent:💰 Using $5000.00 mock capital for simulated trading
INFO:src.bot:⚙️ Analyzing market for trading opportunities...
INFO:src.bot:Generated 12 trading signals across 42 coins
INFO:src.bot:8 signals passed confidence threshold
INFO:src.bot:💱 Executing 3 trades
INFO:src.trading.agent:✅ TRADE: BOUGHT 58.2735 ZORA @ $13.0625 | Total: $761.45
INFO:src.trading.agent:
💰 TRADING ACCOUNT STATUS
Initial Capital: $5000.00
Portfolio Value: $761.45
Available Cash: $4238.55
Total Value: $5000.00
P&L: +$0.00 (+0.00%)
```

## Advanced Usage

### Running with Multiple Strategies

To use multiple trading strategies:

```bash
python run_bot.py --wallet YOUR_WALLET_ADDRESS --strategies SimpleStrategy,MomentumStrategy
```

### Custom Confidence Threshold

To set a custom confidence threshold for trade execution:

```bash
python run_bot.py --wallet YOUR_WALLET_ADDRESS --auto-trade --confidence 0.85
```

This will only execute trades with a confidence score of 0.85 or higher.

### Limiting Trade Amounts

To limit the maximum amount per trade:

```bash
python run_bot.py --wallet YOUR_WALLET_ADDRESS --auto-trade --max-trade-amount 200
```

This limits individual trades to a maximum of $200 USD.

### Disabling WebSocket

If you encounter issues with WebSocket connections:

```bash
python run_bot.py --wallet YOUR_WALLET_ADDRESS --no-websocket
```

This disables WebSocket connections and uses polling instead.

## Command-Line Arguments Reference

| Argument | Description | Default |
|----------|-------------|---------|
| `--wallet` | Wallet address to track | None (Required) |
| `--auto-trade` | Enable automatic trading | False |
| `--max-trade-amount` | Maximum trade amount in USD | 100.0 |
| `--confidence` | Confidence threshold for executing trades | 0.75 |
| `--mock-capital` | Mock capital for simulated trading | 1000.0 |
| `--strategies` | Comma-separated list of trading strategies to use | SimpleStrategy |
| `--no-websocket` | Disable WebSocket connection | False |
| `--signals-only` | Only display signals, do not execute trades | False |

## Directory Structure

The Zora Portia Trading Bot has the following directory structure:

```
zora-portia-bot/
├── .env                   # Environment variables (API keys, private keys)
├── .gitignore             # Git ignore file
├── README.md              # Project documentation
├── config.example.json    # Example configuration file
├── config.json            # User configuration file
├── requirements.txt       # Python dependencies
├── run_bot.py             # Main entry point
├── setup.py               # Package setup file
├── autonomous_trading_bot.py  # Alternative entry point
├── check_wallet.py        # Utility to check wallet balance
├── debug_transaction.py   # Utility for transaction debugging
├── demo_trade.py          # Demo trade script
├── real_trade_demo.py     # Real trading demo script
├── real_trading_test.py   # Real trading test script
├── swap_test.py           # Swap functionality test
├── test_zora_trading.py   # Trading test script
├── zora_bot.log           # Log file
└── src/                   # Source code directory
    ├── __init__.py        # Package initialization
    ├── bot.py             # Main bot class
    ├── config.py          # Configuration handling
    ├── api/               # API clients
    │   ├── __init__.py    # Package initialization
    │   ├── zora.py        # Zora API client
    │   └── portia.py      # Portia AI API client
    ├── models/            # Data models
    │   ├── __init__.py    # Package initialization
    │   ├── coin.py        # Coin data model
    │   ├── portfolio.py   # Portfolio data model
    │   └── signal.py      # Trading signal model
    ├── strategies/        # Trading strategies
    │   ├── __init__.py    # Package initialization
    │   ├── registry.py    # Strategy registry
    │   └── simple.py      # Simple strategy implementation
    ├── trading/           # Trading functionality
    │   ├── __init__.py    # Package initialization
    │   ├── agent.py       # Trading agent
    │   └── zora_trader.py # Zora trading execution
    └── utils/             # Utilities
        ├── __init__.py    # Package initialization
        └── logging.py     # Logging configuration
```

## Monitoring Bot Activity

### Log Files

The bot creates a log file (`zora_bot.log`) that you can monitor to track its activity:

```bash
# View the log file in real-time
tail -f zora_bot.log
```

### Log Levels

The bot uses different log levels:

- **INFO**: Normal operation information
- **WARNING**: Potential issues that don't stop operation
- **ERROR**: Problems that may affect functionality
- **DEBUG**: Detailed information (enabled with debug logging)

To enable debug logging, add to your `.env` file:

```
LOG_LEVEL=DEBUG
```

## Updating the Bot

To update the bot to the latest version:

```bash
# Navigate to the bot directory
cd zora-portia-bot

# Pull the latest changes
git pull

# Update dependencies
pip install -r requirements.txt
```

## Running as a Background Service

### Linux (systemd)

To run the bot as a background service on Linux:

1. Create a systemd service file:

```bash
sudo nano /etc/systemd/system/zora-bot.service
```

2. Add the following content:

```
[Unit]
Description=Zora Portia Trading Bot
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/zora-portia-bot
ExecStart=/path/to/zora-portia-bot/.venv/bin/python run_bot.py --wallet YOUR_WALLET_ADDRESS --auto-trade
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:

```bash
sudo systemctl enable zora-bot.service
sudo systemctl start zora-bot.service
```

4. Check service status:

```bash
sudo systemctl status zora-bot.service
```

### Windows (Task Scheduler)

On Windows, you can use Task Scheduler:

1. Create a batch file (run_bot.bat):

```
@echo off
cd /d "C:\path\to\zora-portia-bot"
call .venv\Scripts\activate.bat
python run_bot.py --wallet YOUR_WALLET_ADDRESS --auto-trade
```

2. Open Task Scheduler and create a new task:
   - Trigger: At startup
   - Action: Start a program
   - Program/script: `C:\path\to\zora-portia-bot\run_bot.bat`

## Next Steps

After successfully setting up and running the bot, consider exploring these next steps:

1. **Fine-tune strategies**: Adjust strategy parameters in config.json
2. **Add more strategies**: Implement custom strategies
3. **Integrate with Portia AI**: Set up AI-enhanced trading
4. **Monitor performance**: Track trade history and performance
5. **Set up notifications**: Configure alerts for important events

## Getting Help

If you encounter issues:

1. **Check the logs**: Most issues can be diagnosed from the log file
2. **Review documentation**: Ensure you're following the correct procedures
3. **Check common issues**: Refer to the troubleshooting section
4. **Community support**: Join the Zora trading community for help

## Conclusion

Congratulations! You've successfully installed and configured the Zora Portia Trading Bot. Start with simulation mode to learn how the bot works before considering real trading. Remember that cryptocurrency trading involves risk, and past performance is not indicative of future results.

Remember to regularly update the bot and monitor its performance to ensure optimal operation.
