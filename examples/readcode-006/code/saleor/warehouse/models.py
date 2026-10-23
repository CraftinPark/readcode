# saleor/warehouse/models.py from saleor/saleor at 6c450429d3 (lines 377-400; other code removed).
# BSD-3-Clause, see LICENSE-saleor.txt.

class Stock(models.Model):
    warehouse = models.ForeignKey(Warehouse, null=False, on_delete=models.CASCADE)
    product_variant = models.ForeignKey(
        ProductVariant, null=False, on_delete=models.CASCADE, related_name="stocks"
    )
    quantity = models.IntegerField(default=0)
    quantity_allocated = models.IntegerField(default=0)

    objects = StockManager()

    class Meta:
        unique_together = [["warehouse", "product_variant"]]
        ordering = ("pk",)

    def increase_stock(self, quantity: int, commit: bool = True):
        """Return given quantity of product to a stock."""
        self.quantity = F("quantity") + quantity
        if commit:
            self.save(update_fields=["quantity"])

    def decrease_stock(self, quantity: int, commit: bool = True):
        self.quantity = F("quantity") - quantity
        if commit:
            self.save(update_fields=["quantity"])
