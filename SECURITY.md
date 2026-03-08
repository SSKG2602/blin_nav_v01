# Security

## Secrets and credentials

- do not commit `.env` files, API keys, auth tokens, merchant accounts, or personal data
- use `.env.example` as the template for local configuration
- keep `GEMINI_API_KEY`, database credentials, and Redis connection details out of source control

## Auth and token handling

The repo includes lightweight auth for demo-grade identity and session continuity. Treat it as an application surface, not as production-grade enterprise identity infrastructure.

- do not expose bearer tokens in screenshots, logs, or docs
- do not hardcode auth tokens into scripts or tests
- keep local demo accounts separate from personal merchant accounts where possible

## Checkout and payment boundaries

BlindNav must preserve its safety boundaries:

- OTP, CAPTCHA, and payment-auth events require explicit assisted checkpoints
- final purchase placement requires explicit final confirmation
- the agent must not silently continue through sensitive checkpoints
- low-confidence conditions should halt or recover, not guess

## Browser-runtime safety

- keep merchant credentials and live shopping sessions within trusted local or controlled deployment environments
- do not weaken verification or trust checks to make demos look smoother
- do not bypass runtime grounding with fabricated product, cart, or order state

## Logs and user-verifiable artifacts

The repo persists session logs and closure artifacts for transparency. Handle them as sensitive operational records:

- avoid storing secrets or raw credentials in logs
- avoid copying live personal order data into issue trackers or public docs
- sanitize any demo captures before external sharing

## Responsible disclosure

If you discover a security issue and there is no formal disclosure channel yet, use a private maintainer contact path rather than opening a public exploit description in an issue.

Until a formal process is published, treat private maintainer outreach as the default disclosure path.
