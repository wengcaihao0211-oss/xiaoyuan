# Homepage Query Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent the Vercel homepage invocation from timing out by eliminating per-product image queries.

**Architecture:** Keep the existing Flask routes and templates, but make the product-image relationship eager-loadable and preload it for homepage product lists. The product-card template will resolve the cover image once per card. A regression test will assert that homepage SQL query count remains bounded with several products.

**Tech Stack:** Python, Flask, Flask-SQLAlchemy, SQLAlchemy, pytest

---

### Task 1: Bound Homepage Database Queries

**Files:**
- Create: `tests/test_homepage_queries.py`
- Modify: `app/models/product.py:27-48`
- Modify: `app/blueprints/browse/routes.py:12-22`
- Modify: `app/templates/partials/_product_card.html:1-12`

- [ ] **Step 1: Write the failing regression test**

Create an isolated SQLite database, insert seven categories, one seller, six
on-sale products, and one image per product. Count SQL statements while
requesting `/`, then assert the response is 200 and no more than six statements
are executed.

- [ ] **Step 2: Run the regression test to verify it fails**

Run:

```powershell
python -m pytest tests/test_homepage_queries.py -v
```

Expected: FAIL because the dynamic `images` relationship issues additional
queries for each rendered product card.

- [ ] **Step 3: Implement eager image loading**

Change `Product.images` to a select-in relationship ordered by
`ProductImage.sort_order`. Update `cover_image` and `image_list` to read the
loaded collection. Add `selectinload(Product.images)` to both homepage product
queries. Bind `product.cover_image` to a template variable before the image
condition.

- [ ] **Step 4: Run the regression test to verify it passes**

Run:

```powershell
python -m pytest tests/test_homepage_queries.py -v
```

Expected: PASS with a bounded query count.

- [ ] **Step 5: Run full verification**

Run:

```powershell
python -m pytest -v
python -m compileall -q app api
```

Then request `/`, `/ping`, and `/db-test` with Flask's test client and verify all
return HTTP 200.

- [ ] **Step 6: Commit the fix**

```powershell
git add tests/test_homepage_queries.py app/models/product.py app/blueprints/browse/routes.py app/templates/partials/_product_card.html docs/superpowers/plans/2026-06-22-homepage-query-optimization.md
git commit -m "fix: preload homepage product images"
```
