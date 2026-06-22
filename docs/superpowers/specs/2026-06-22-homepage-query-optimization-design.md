# Homepage Query Optimization Design

## Problem

The homepage loads up to two product lists. Each product card reads
`product.cover_image`, and the template currently reads that property twice.
Because `Product.images` is a dynamic relationship, every property read issues
another SQL query. With a remote Supabase database this creates many network
round trips during one Vercel invocation and can exceed the function runtime.

## Design

- Change `Product.images` from a dynamic relationship to a queryable
  relationship that supports eager loading.
- Eager-load product images in the homepage product queries.
- Resolve `cover_image` from the already-loaded image collection.
- Bind `cover_image` once in the product-card template so it is not evaluated
  repeatedly.

Other relationship behavior and page output remain unchanged.

## Verification

- Add a regression test that creates multiple on-sale products and requests the
  homepage.
- Assert the response succeeds.
- Count SQL statements and assert the homepage query count stays bounded rather
  than increasing per rendered product.
- Run the full test suite and a direct local homepage request.

## Risks

Changing the relationship loader can affect code that calls
`product.images.order_by(...)`. Those call sites must be updated to sort the
loaded collection or query `ProductImage` explicitly.
