Product Specifications: E-Shop Checkout

Discount Codes

Code: "SAVE15"

Effect: Applies a 15% discount to the subtotal.

Constraint: Only one discount code can be applied at a time.

Invalid Codes: Any code other than "SAVE15" should be rejected with an error message.

Shipping Methods

Standard Shipping: Cost is $0.00 (Free).

Express Shipping: Cost is $10.00 flat rate.

Cart Calculations

Subtotal: Sum of (Item Price * Quantity).

Discount Amount: Subtotal * 0.15 (if valid code applied).

Total: (Subtotal - Discount Amount) + Shipping Cost.

Updates: The total must update immediately when shipping method changes or items are added/removed.