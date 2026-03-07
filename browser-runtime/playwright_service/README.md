# Playwright Service Placeholder

This directory reserves the browser automation runtime boundary for BlindNav.

Current status:
- no service implementation
- no selectors
- no page models
- no merchant logic

Purpose of the placeholder:
- make the runtime boundary explicit
- pin Playwright Python as the intended automation path
- keep future browser code separate from the FastAPI app

Primary merchant target remains `amazon.in`. Flipkart and Meesho are backup contingencies only and are not implemented here.
