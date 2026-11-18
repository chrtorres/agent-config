# Tracker logging-storm case

An Ubuntu startup slowdown coincided with Tracker filesystem-miner assertions (`g_file_equal`, invalid objects and SPARQL constraints), 10,000 journal messages in a 30-second window, elevated logging CPU and an approximately 80 GiB syslog. Stopping the miner stopped log growth. A later user-applied filesystem-index reset and restart completed indexing without the storm. Three images still failed metadata extraction; that was distinct from the database error loop.

Reusable verification: compare service state and `tracker3 status` before and after a short interval; inspect fresh journal entries for the actual PID or unit, and measure syslog growth. A truncated SYSLOG_IDENTIFIER can cause a `journalctl -t` query to miss messages; cross-check the unit or PID before interpreting zero matches.

The user separately authorized and executed stopping/resetting/restarting Tracker and truncating syslog. Those actions delete index state or log evidence and are not authorized by this diagnostic skill. Historical log cleanup did not remove a separate large rotated log. Preserve evidence and discuss retention before proposing cleanup.
