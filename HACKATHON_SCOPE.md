# Hackathon Scope

BlindNav is built for the Gemini Live Agent Challenge as a bounded, implementation-grounded accessibility shopping agent. This document summarizes the scope actually implemented in this repo.

## Implemented demo-visible scope

The current repo implements the bounded nopCommerce demo flow for:

- wake-word and typed interaction through the operator shell
- spoken shopping intent capture and websocket `user_text`
- browser-native spoken replies in the shell
- clarification for incomplete or ambiguous requests
- merchant trust verification
- visual page understanding
- browser-grounded search, result interpretation, and product verification
- configurable-product and minimum-quantity blocker detection
- cart verification
- checkout-entry recognition with an intentional stop before guest checkout
- browser activity visibility through screenshot, URL, and status polling
- final user-verifiable logs and spoken summaries

## Implemented system support

The repo also includes bounded system support for:

- efficiency control and duplicate-action suppression
- lightweight auth and user-scoped session history
- desynchronization recovery
- layout-change resilience and UI stabilization
- operator-visible audit logs and session context

## Deliberate boundaries

BlindNav here is:

- deterministic, not unconstrained
- browser-grounded, not blind-action automation
- bounded to the current demo flow and single rehearsed public merchant path
- honest about the checkout-entry stop boundary

BlindNav here is not claimed to be:

- a generalized multi-merchant autonomous shopper
- a production-grade checkout autopilot
- a guest-checkout executor
- a payment or order-placement automation system
- a post-purchase or delivery-management demo

## Scope grounding note

`Gemini_Hack` remains the intended reference boundary. This repo documents only the subset that is actually implemented and demo-ready here.
