# Hackathon Scope

BlindNav is built for the Gemini Live Agent Challenge as a bounded, implementation-grounded accessibility shopping agent. This document summarizes the scope actually implemented in this repo, using the sibling `Gemini_Hack` material as the intended reference boundary.

## Implemented demo-visible scope

The current repo implements the bounded non-future flow for:

- wake and live voice interaction through the operator shell
- multilingual interaction path
- spoken shopping intent capture
- clarification for incomplete or ambiguous intent
- merchant trust verification
- visual page understanding
- browser-grounded navigation and result interpretation
- candidate ranking and differentiation
- product and variant verification
- review risk assessment and spoken review takeaway
- interruption and safe backend re-anchoring
- cart and checkout verification
- sensitive checkpoints for OTP, CAPTCHA, and payment-auth events
- final verbal confirmation before purchase
- final user-verifiable session summary
- basic post-purchase support and latest-order handling

## Implemented system support

The repo also includes bounded system support for:

- efficiency control and duplicate-action suppression
- lightweight auth and user-scoped session history
- desynchronization recovery
- layout-change resilience and UI stabilization
- multi-product cart context
- post-purchase order tracking support for the latest order context

## Deliberate boundaries

BlindNav here is:

- deterministic, not unconstrained
- browser-grounded, not blind-action automation
- bounded to the current demo flow and supported merchant path
- honest about current implementation state

BlindNav here is not claimed to be:

- a generalized multi-merchant autonomous shopper
- a production-grade checkout autopilot
- a full returns automation system
- a proactive delivery-alert platform
- a long-term preference or reordering engine

## Scope grounding note

`Gemini_Hack` remains the intended-scope and workflow reference. This repo documents only the subset that is actually implemented and runnable here.
