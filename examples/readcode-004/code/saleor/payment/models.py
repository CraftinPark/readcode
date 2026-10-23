# saleor/payment/models.py from saleor/saleor at 6e02394579 (lines 158-207; other code removed).
# BSD-3-Clause, see LICENSE-saleor.txt.

class TransactionEvent(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=128,
        choices=TransactionEventStatus.CHOICES,
        default=TransactionEventStatus.SUCCESS,
        blank=True,
        null=True,
    )
    psp_reference = models.CharField(max_length=512, blank=True, null=True)
    message = models.CharField(max_length=512, blank=True, null=True, default="")
    transaction = models.ForeignKey(
        TransactionItem, related_name="events", on_delete=models.CASCADE
    )
    external_url = models.URLField(blank=True, null=True)
    currency = models.CharField(max_length=settings.DEFAULT_CURRENCY_CODE_LENGTH)
    type = models.CharField(
        max_length=128,
        choices=TransactionEventType.CHOICES,
        default=TransactionEventType.INFO,
    )
    amount = MoneyField(amount_field="amount_value", currency_field="currency")
    amount_value = models.DecimalField(
        max_digits=settings.DEFAULT_MAX_DIGITS,
        decimal_places=settings.DEFAULT_DECIMAL_PLACES,
        default=Decimal("0"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    # We store app and app_identifier, as the app field stores apps of
    # all types (local, third-party), and the app_identifier field stores
    # only third-party apps.
    # In the case of re-installing the third-party app, we are able to match
    # existing transactions with the re-installed app by using `app_identifier`.
    app = models.ForeignKey(
        "app.App", related_name="+", null=True, blank=True, on_delete=models.SET_NULL
    )
    app_identifier = models.CharField(blank=True, null=True, max_length=256)

    include_in_calculations = models.BooleanField(default=False)

    class Meta:
        ordering = ("pk",)
