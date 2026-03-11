# Demo Notes

BlindNav is demonstrated through a bounded operator shell flow, not through opaque autonomous shopping.

## Demo path highlights

- live session creation from the web shell
- wake phrase plus spoken or typed shopping intent capture
- browser-native spoken replies from backend `spoken_output`
- deterministic backend progression through search, product verification, cart, checkout, and post-purchase support
- browser activity visibility through screenshot thumbnail, URL, and status updates
- explicit clarification, checkpoint, and final-confirmation states
- no merchant cookie-connect step in the public shell
- latest-order support and bounded order cancellation
- low-confidence halt and recovery visibility

## Demo boundary

- active demo merchant: `demo.nopcommerce.com`
- search, product, cart, and runtime visibility are the active Phase 1 public surfaces
- checkout and order-history behavior should be described conservatively unless later phases validate them
- the demo emphasizes trust, verification, and consent rather than broad merchant coverage
- future-scope features that are not in the runnable repo should not be presented as complete during judging or onboarding

See [HACKATHON_SCOPE.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/HACKATHON_SCOPE.md) for the current scope statement.
