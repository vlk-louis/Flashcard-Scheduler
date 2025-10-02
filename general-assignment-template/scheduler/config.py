MAX_INTERVAL_SECONDS = 365 * 24 * 3600
RETRY_SECONDS = 60
FIRST_INTERVAL = {
    1: 24 * 3600,      # 1 day
    2: 4 * 24 * 3600,  # 4 days (longest initial)
}
GROWTH = {
    1: 1.6,            # moderate growth
    2: 2.5,            # faster growth
}