# Token Contract Documentation

## Overview

ERC20-compatible token implementation in Solidity.

## Contract Interface

```solidity
interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address to, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
}
```

## Deployment

### Constructor Parameters
- `name`: Token name (e.g., "QENEX Token")
- `symbol`: Token symbol (e.g., "QXC")
- `decimals`: Decimal places (typically 18)
- `supply`: Initial supply (before decimals)

### Example Deployment
```javascript
const Token = await ethers.getContractFactory("Token");
const token = await Token.deploy(
    "QENEX Token",
    "QXC",
    18,
    1000000  // 1,000,000 tokens
);
await token.deployed();
```

## Functions

### View Functions

**totalSupply()**
Returns the total token supply.
```solidity
uint256 supply = token.totalSupply();
```

**balanceOf(address)**
Returns token balance of an address.
```solidity
uint256 balance = token.balanceOf(userAddress);
```

**allowance(address owner, address spender)**
Returns approved amount for spending.
```solidity
uint256 allowed = token.allowance(owner, spender);
```

### State-Changing Functions

**transfer(address to, uint256 amount)**
Transfer tokens to another address.
```solidity
bool success = token.transfer(recipient, 1000);
```

**approve(address spender, uint256 amount)**
Approve spender to use tokens.
```solidity
bool success = token.approve(spender, 5000);
```

**transferFrom(address from, address to, uint256 amount)**
Transfer tokens on behalf of another address.
```solidity
bool success = token.transferFrom(owner, recipient, 1000);
```

## Events

**Transfer**
Emitted on token transfers.
```solidity
event Transfer(
    address indexed from,
    address indexed to,
    uint256 value
);
```

**Approval**
Emitted on approval changes.
```solidity
event Approval(
    address indexed owner,
    address indexed spender,
    uint256 value
);
```

## Security Features

### Zero Address Checks
- Prevents transfers to 0x0 address
- Prevents approvals to 0x0 address

### Balance Validation
- Checks sufficient balance before transfer
- Validates allowance before transferFrom

### Safe Math
- Solidity 0.8+ automatic overflow protection
- No need for SafeMath library

## Usage Examples

### Basic Transfer
```javascript
// Connect to token contract
const token = await ethers.getContractAt("Token", tokenAddress);

// Transfer 100 tokens (with 18 decimals)
const amount = ethers.utils.parseEther("100");
await token.transfer(recipientAddress, amount);
```

### Approval Pattern
```javascript
// Approve spender
const amount = ethers.utils.parseEther("500");
await token.approve(spenderAddress, amount);

// Spender transfers tokens
await token.connect(spender).transferFrom(
    ownerAddress,
    recipientAddress,
    amount
);
```

### Reading Balances
```javascript
// Get balance
const balance = await token.balanceOf(address);
const formatted = ethers.utils.formatEther(balance);
console.log(`Balance: ${formatted} tokens`);
```

## Gas Optimization

- Efficient storage patterns
- Minimal external calls
- Optimized for common operations

## Integration

### Web3.js
```javascript
const contract = new web3.eth.Contract(ABI, address);
const balance = await contract.methods.balanceOf(account).call();
```

### Ethers.js
```javascript
const contract = new ethers.Contract(address, ABI, provider);
const balance = await contract.balanceOf(account);
```

## Testing

```javascript
describe("Token", function() {
    it("Should transfer tokens", async function() {
        const [owner, addr1] = await ethers.getSigners();
        const Token = await ethers.getContractFactory("Token");
        const token = await Token.deploy("Test", "TST", 18, 1000);
        
        await token.transfer(addr1.address, 100);
        expect(await token.balanceOf(addr1.address)).to.equal(100);
    });
});
```

## Auditing Checklist

- ✓ No external dependencies
- ✓ Zero address validations
- ✓ Balance checks
- ✓ Allowance management
- ✓ Event emissions
- ✓ Standard compliance