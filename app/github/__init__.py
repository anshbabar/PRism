"""GitHub App integration (Milestone 7).

Turns PRism into a real GitHub App: verify webhook signatures, authenticate as an
installation, fetch a PR's diff, and post a single concise review. All PR content
is untrusted; posting is gated behind ``POST_REVIEWS`` (dry-run by default).
"""
