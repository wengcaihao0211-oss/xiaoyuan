from flask import request, current_app


class ListPagination:
    """Simple pagination wrapper for list-based collections."""
    def __init__(self, items, page, per_page, total):
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = ((total - 1) // per_page + 1) if total > 0 else 0

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def prev_num(self):
        return self.page - 1

    @property
    def next_num(self):
        return self.page + 1

    def iter_pages(self, left_edge=2, left_current=2, right_current=4, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if (
                num <= left_edge
                or (num > self.page - left_current - 1 and num < self.page + right_current)
                or num > self.pages - right_edge
            ):
                if last + 1 != num:
                    yield None
                yield num
                last = num


def get_page(value=None):
    """Get a normalized page number from an explicit value or request args."""
    try:
        if value is None:
            value = request.args.get('page', 1)
        page = int(value)
        return max(1, page)
    except (ValueError, TypeError):
        return 1


def paginate(query, per_page=None):
    """Paginate a SQLAlchemy query. Returns a Pagination object."""
    if per_page is None:
        per_page = current_app.config.get('ITEMS_PER_PAGE', 12)
    page = get_page()
    return query.paginate(page=page, per_page=per_page, error_out=False)
