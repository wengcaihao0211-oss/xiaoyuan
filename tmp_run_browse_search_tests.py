from tests.test_browse_search import (
    test_search_matches_name_and_description_and_trims_keyword,
    test_search_empty_keyword_returns_all_on_sale_products,
    test_search_rejects_too_long_keyword,
    test_search_escapes_sql_wildcards_and_keeps_query_semantics,
    test_search_supports_pagination_and_sorting,
    test_hot_keyword_search_can_be_cached,
)

test_search_matches_name_and_description_and_trims_keyword()
print('test_search_matches_name_and_description_and_trims_keyword: ok')
test_search_empty_keyword_returns_all_on_sale_products()
print('test_search_empty_keyword_returns_all_on_sale_products: ok')
test_search_rejects_too_long_keyword()
print('test_search_rejects_too_long_keyword: ok')
test_search_escapes_sql_wildcards_and_keeps_query_semantics()
print('test_search_escapes_sql_wildcards_and_keeps_query_semantics: ok')
test_search_supports_pagination_and_sorting()
print('test_search_supports_pagination_and_sorting: ok')
test_hot_keyword_search_can_be_cached()
print('test_hot_keyword_search_can_be_cached: ok')
print('ALL_OK')
