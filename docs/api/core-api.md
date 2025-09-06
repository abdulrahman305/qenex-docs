# Core API Reference

## QenexFinancialOS

Main financial operating system class.

### Methods

#### `initialize()`
Initialize the financial OS with all components.

```python
financial_os = QenexFinancialOS()
await financial_os.initialize()
```

#### `create_account(user_id, account_type, currency)`
Create a new financial account.

**Parameters:**
- `user_id` (str): User identifier
- `account_type` (str): Type of account (CHECKING, SAVINGS, etc.)
- `currency` (str): Currency code (USD, EUR, etc.)

**Returns:** Account object

```python
account = await financial_os.create_account(
    user_id="user123",
    account_type="CHECKING", 
    currency="USD"
)
```

#### `process_payment(payment_data)`
Process a payment transaction.

**Parameters:**
- `payment_data` (dict): Payment details

**Returns:** Transaction ID

```python
result = await financial_os.process_payment({
    'from_account': 'account_123',
    'to_account': 'account_456',
    'amount': 1000.00,
    'currency': 'USD',
    'type': 'TRANSFER'
})
```
