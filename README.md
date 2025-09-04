# QENEX Documentation

Technical documentation for the QENEX ecosystem.

## Components

### [Core System](./core.md)
Python framework providing authentication, caching, and database management.

### [DeFi Platform](./defi.md)
Decentralized finance implementation with AMM and liquidity pools.

### [Token Contract](./token.md)
ERC20-compatible token smart contract.

## Quick Start

1. **Install Core System**
   ```bash
   git clone https://github.com/abdulrahman305/qenex-os.git
   cd qenex-os
   pip install -r requirements.txt
   python core.py
   ```

2. **Setup DeFi Platform**
   ```bash
   git clone https://github.com/abdulrahman305/qenex-defi.git
   cd qenex-defi
   python defi.py
   ```

3. **Deploy Token Contract**
   ```bash
   git clone https://github.com/abdulrahman305/qxc-token.git
   cd qxc-token
   # Deploy using preferred Ethereum toolchain
   ```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Core API   │────▶│ DeFi Engine  │────▶│ Token Smart  │
│   (Python)  │     │   (Python)   │     │  Contract    │
└─────────────┘     └──────────────┘     └──────────────┘
       │                    │                     │
       ▼                    ▼                     ▼
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   SQLite    │     │   Liquidity  │     │  Blockchain  │
│  Database   │     │    Pools     │     │   Network    │
└─────────────┘     └──────────────┘     └──────────────┘
```

## Development

### Prerequisites
- Python 3.8+
- SQLite3
- Node.js (for smart contract deployment)

### Testing
```bash
# Core tests
cd qenex-os && python -m pytest

# DeFi tests  
cd qenex-defi && python -m pytest

# Contract tests
cd qxc-token && npm test
```

## Security

- Password hashing with PBKDF2
- Session-based authentication
- SQL injection prevention
- Input validation
- Rate limiting

## License

MIT License - See individual repositories for details.