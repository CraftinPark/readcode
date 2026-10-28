ACTIVE = "active"
PAST_DUE = "past_due"      # last charge failed; dunning retries it at the next renewal
TRIALING = "trialing"      # period_end == trial_end; the first renewal converts the trial
CANCELLED = "cancelled"
