# Demo Operator Guide

## Pre-demo checklist

- use Chrome or Edge for the full wake-word and browser-native speech path
- start the three local services or confirm the deployed frontend, backend, and browser-runtime are healthy
- confirm `demo.nopcommerce.com` is reachable from the browser-runtime
- sign in to the operator shell before starting the live session
- confirm the `Browser Activity` panel is updating
- confirm microphone permission is granted if you are using wake flow
- confirm you can see transcript, spoken replies, and audit/log panels

## Exact bounded demo flow

1. Start a live session.
2. Click `Wake Luminar` or use typed input if voice capture is unavailable.
3. Use a happy-path request such as `Luminar, find one m8`.
4. Let BlindNav search, verify the product, add it to cart, and read back the cart.
5. Let BlindNav recognize checkout entry.
6. Stop when the spoken summary says checkout entry was reached and BlindNav is stopping before guest checkout.

## Spoken checkpoints to expect

- `Results loaded. I found 1 candidate on the demo store.`
- `Product verified: HTC One M8 Android L 5.0 Lollipop at $245.00.`
- `Added to cart: HTC One M8 Android L 5.0 Lollipop. Cart verified with 1 item.`
- `Checkout entry reached for HTC One M8 Android L 5.0 Lollipop. Stopping before guest checkout.`

## Golden happy-path script

Recommended spoken prompt:

```text
Luminar, find one m8
```

Expected operator-visible behavior:

- search results are loaded and summarized
- the simple HTC product is opened and verified
- add-to-cart succeeds with real cart evidence
- cart is read back coherently
- checkout entry is recognized
- BlindNav stops before guest checkout

## Blocker-path script

Recommended spoken prompt:

```text
Luminar, find build your own computer
```

Expected behavior:

- BlindNav opens the configurable product
- required options are recognized
- no blind add-to-cart happens
- the operator hears a blocker summary such as:

```text
Product blocked before add to cart. Build your own computer still needs required options selected.
```

- audit/log output should expose the blocker reason

## Recovery-path script

Use this if you want to show safety instead of happy-path completion.

Expected behavior when the runtime hits modal interruption or selector/layout drift:

- recovery is prioritized before optimistic continuation
- no unsafe add-to-cart or checkout action occurs
- the operator hears a summary such as:

```text
Recovery engaged on product_detail. Page indicates modal interruption signals.
```

- audit/log output should expose the recovery reason

## Checkout stop wording

Use this exact framing in the demo:

- BlindNav recognizes checkout entry.
- BlindNav intentionally stops before guest checkout.
- Full checkout, payment, and order placement are outside the current demo scope.

## Fallback instructions if live behavior drifts

- if speech capture fails, switch to typed input and continue the same flow
- if the happy-path product drifts, return to the home page and retry the simple product search
- if nopCommerce layout changes, show the recovery path instead of forcing the happy path
- if a product shows required options or minimum quantity, treat that as a valid blocker demo, not an error to hide
- if checkout entry does not appear, stop at cart verification and explain the bounded stop honestly

## What not to click or say

- do not click `Checkout as Guest`
- do not manually push through address, shipping, payment, or order placement
- do not claim an order was placed
- do not describe the demo as full checkout automation
- do not switch to unsupported merchants
