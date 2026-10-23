# saleor/payment/gateway.py from saleor/saleor at 6e02394579 (lines 119-155, 211-260; other code removed).
# BSD-3-Clause, see LICENSE-saleor.txt.

def request_refund_action(
    transaction: TransactionItem,
    manager: "PluginsManager",
    refund_value: Optional[Decimal],
    request_event: TransactionEvent,
    channel_slug: str,
    user: Optional[User],
    app: Optional[App],
):
    if refund_value is None:
        refund_value = transaction.charged_value

    transaction_action_data = _create_transaction_data(
        transaction=transaction,
        action_type=TransactionAction.REFUND,
        action_value=refund_value,
        request_event=request_event,
    )
    _request_payment_action(
        transaction_action_data=transaction_action_data,
        manager=manager,
        channel_slug=channel_slug,
        event_type=WebhookEventSyncType.TRANSACTION_REFUND_REQUESTED,
        transaction_request_func=manager.transaction_refund_requested,
        plugin_func_name="transaction_refund_requested",
    )

    if order_id := transaction.order_id:
        event_transaction_refund_requested(
            order_id=order_id,
            reference=transaction.psp_reference or "",
            amount=quantize_price(refund_value, transaction.currency),
            user=user,
            app=app,
        )

# ...

def _request_payment_action(
    transaction_action_data: "TransactionActionData",
    manager: "PluginsManager",
    channel_slug: str,
    event_type: str,
    transaction_request_func: Callable[[TransactionActionData, str], None],
    plugin_func_name: str,
):
    transaction_action_request_event_active = manager.is_event_active_for_any_plugin(
        "transaction_action_request", channel_slug=channel_slug
    )

    transaction_request_event_active = manager.is_event_active_for_any_plugin(
        plugin_func_name, channel_slug=channel_slug
    )

    webhooks = None
    if transaction_action_data.transaction_app_owner:
        webhooks = get_webhooks_for_event(
            event_type=event_type,
            apps_ids=[transaction_action_data.transaction_app_owner.pk],
        )

    if (
        not transaction_action_request_event_active
        and not transaction_request_event_active
        and not webhooks
    ):
        create_failed_transaction_event(
            transaction_action_data.event,
            cause="No app or plugin is configured to handle payment action requests.",
        )
        raise PaymentError(
            "No app or plugin is configured to handle payment action requests."
        )

    if transaction_request_event_active or webhooks:
        # This if can be dropped in future releases as VOID will be dropped.
        if transaction_action_data.action_type == TransactionAction.VOID:
            transaction_action_data.action_type = TransactionAction.CANCEL
        transaction_request_func(transaction_action_data, channel_slug)
    else:
        manager.transaction_action_request(
            transaction_action_data, channel_slug=channel_slug
        )


@raise_payment_error
@require_active_payment
@with_locked_payment
