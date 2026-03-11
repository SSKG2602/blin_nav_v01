# Demo Overview

BlindNav is demonstrated through a bounded operator-guided flow on `demo.nopcommerce.com`. The demo is designed to be repeatable, safety-preserving, and easy to judge without claiming unsupported checkout automation.

## Active demo path

- home page landing
- search submission
- search result extraction and spoken summary
- product verification
- safe add-to-cart when supported
- cart verification
- checkout-entry recognition
- intentional stop before guest checkout

## Supported scenario types

- golden happy path: simple supported product reaches cart and then checkout entry recognition
- blocker path: configurable or otherwise blocked product triggers clarification or safe halt before add-to-cart
- recovery path: modal interruption or selector/layout drift triggers deterministic recovery or safe halt

## Hard boundaries

- do not present BlindNav as full checkout automation
- do not click `Checkout as Guest`
- do not imply order placement or payment completion
- do not claim multi-merchant autonomy beyond `demo.nopcommerce.com`

## Use these docs during a demo

- [docs/demo/OPERATOR_GUIDE.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/docs/demo/OPERATOR_GUIDE.md) for the live script, setup checklist, and fallback instructions
- [docs/demo/EVIDENCE.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/docs/demo/EVIDENCE.md) for the current green scenarios, latest pass counts, and intentional skips
- [TESTING.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/TESTING.md) for local commands
- [TROUBLESHOOTING.md](/Users/shreyasshashi/Desktop/Gemini_Project/skms#7864/TROUBLESHOOTING.md) for known issues and safe fallback behavior
