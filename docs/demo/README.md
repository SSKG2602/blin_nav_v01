# Demo Notes

BlindNav is demonstrated through a bounded operator shell flow, not through opaque autonomous shopping.

## Demo path highlights

- live session creation from the web shell
- wake phrase plus spoken or typed shopping intent capture
- browser-native spoken replies from backend `spoken_output`
- deterministic backend progression through nopCommerce home, search, product verification, cart, and checkout-entry recognition
- browser activity visibility through screenshot thumbnail, URL, and status updates
- explicit clarification, checkpoint, and final-confirmation states
- no merchant cookie-connect step in the public shell
- bounded configurable-product blocking when required options are not selected
- low-confidence halt and recovery visibility

## Demo boundary

- active demo merchant: `demo.nopcommerce.com`
- active Phase 2 surfaces are home, search/listing, product detail, cart, and guest-checkout entry recognition
- deeper guest checkout, payment, order placement, and order-history behavior remain deferred
- configurable products that require option selection should halt safely instead of being forced through add-to-cart
- the demo emphasizes trust, verification, and consent rather than broad merchant coverage
- future-scope features that are not in the runnable repo should not be presented as complete during judging or onboarding

See [HACKATHON_SCOPE.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/HACKATHON_SCOPE.md) for the current scope statement.
