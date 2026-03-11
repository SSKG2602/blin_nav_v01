# Troubleshooting

## Backend will not start

Check:

- `.env` exists at the repo root
- PostgreSQL is reachable at `DATABASE_URL`
- Redis is reachable at `REDIS_URL`
- Python dependencies are installed under the expected virtual environment

Useful commands:

```bash
docker compose ps postgres redis
curl http://localhost:8100/health
curl http://localhost:8100/health/ready
```

## Browser runtime is unavailable

Check:

- the runtime process is running on port `8200`
- Playwright dependencies are installed
- the backend `BROWSER_RUNTIME_BASE_URL` matches the runtime host

Useful command:

```bash
curl http://localhost:8200/health/live
```

## Frontend cannot reach the backend

Check:

- `NEXT_PUBLIC_API_BASE_URL` is set correctly
- the backend is listening on `8100`
- `FRONTEND_ORIGIN` matches the deployed or local frontend host
- websocket traffic to the backend is not blocked by origin or proxy settings

## Gemini-backed features are failing

Check:

- `GEMINI_API_KEY` is set
- the configured Gemini model names point to the intended Gemini 2.5 Flash deployment target
- outbound network access is available from the backend environment

If Gemini is unavailable, interpretation and summarization quality may degrade, but deterministic orchestration should remain intact.

## Wake word is not triggering

Check:

- you are using Chrome or Edge
- microphone permission was granted when `Wake Luminar` was clicked
- the shell entered wake-listening state
- the websocket session is active after the wake button was pressed

If voice capture is unstable, fall back to typed input and run the same bounded demo flow.

## Browser-native TTS is not speaking

Check:

- the browser allows audio playback
- `window.speechSynthesis` is available
- the backend is emitting `spoken_output`
- the shell is not muted by autoplay or OS-level output settings

## Browser activity panel is blank or stale

Check:

- the browser-runtime is reachable through the backend
- `GET /api/sessions/{session_id}/runtime/screenshot` is returning data
- the session is active and the shell is polling runtime screenshots
- the current page is still available to the browser-runtime session

## Demo store session is not opening correctly

Check:

- a live session was started from the shell
- the runtime can reach `demo.nopcommerce.com`
- the `Browser Activity` panel is updating after session start
- the runtime observation route is returning a current URL instead of repeated navigation placeholders

## Add-to-cart is blocked on a product page

Check:

- the page is a supported nopCommerce product detail page
- the product does not require unresolved attribute selection such as `Processor *` or `RAM *`
- the quantity input does not advertise a minimum quantity above `1`
- the runtime reported a real success signal such as a cart badge increase or cart verification

If the runtime reports `option_selection_required` or `minimum_quantity_required`, the halt is intentional.

## Checkout entry is reached and the flow stops

This is expected in the current demo.

Check:

- the cart page exposed the `Checkout` control
- any visible terms-of-service checkbox was handled safely
- the runtime reached `demo.nopcommerce.com/login/checkoutasguest` or equivalent guest/sign-in entry

BlindNav must stop before guest checkout. Do not click `Checkout as Guest`, and do not describe this as full checkout automation.

## Recovery is triggered instead of continuing

Recovery is the correct outcome when the runtime sees:

- modal interruption
- selector degradation
- layout drift
- page/state desynchronization

If this happens during a live demo, either show the recovery behavior as an intentional safety feature or restart from the nopCommerce home page and retry the happy-path product.

## Pytest logs show database metadata warnings

Some backend tests log PostgreSQL metadata initialization retries before dependency overrides take over.

Interpretation:

- this is environment noise in the current local setup
- it does not mean the bounded test run failed if pytest still exits successfully

## Frontend production build fails in this workspace path

If the repo path contains `#`, Next.js tracing can fail during `npm run build` or `next build`.

Workaround:

- copy or clone the repo into a path without `#`
- rerun the frontend checks there

## Audit logs or spoken summaries look surprising

Use the bounded contract when reading them:

- `Results loaded...` means search/listing evidence is stable enough to proceed
- `Product verified...` means a candidate passed bounded verification
- `Added to cart... Cart verified...` means the cart had real confirmation evidence
- `Checkout entry reached... Stopping before guest checkout.` is the intentional stop boundary

If the logs show blocker or recovery reasons instead, treat that as valid safety behavior, not a failed demo by default.
