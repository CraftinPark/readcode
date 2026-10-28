ACTIVE = "active"
PAST_DUE = "past_due"      # last charge failed; dunning retries it at the next renewal
TRIALING = "trialing"      # period_end == trial_end; the first renewal converts the trial
CANCELLED = "cancelled"
# Written by other systems straight into production (not by this repo):
CANCEL_PENDING = "cancel_pending"    # support console: cancel at the end of the paid period, never renew
ACTIVE_MIGRATED = "active_migrated"  # July 2026 legacy-plan migration: paying customers, bill as active
BILLABLE = (ACTIVE, PAST_DUE, TRIALING, ACTIVE_MIGRATED)
