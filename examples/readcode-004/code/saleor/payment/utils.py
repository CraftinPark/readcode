# saleor/payment/utils.py from saleor/saleor at 6e02394579 (lines 923-936, 1015-1045, 1083-1273; other code removed).
# BSD-3-Clause, see LICENSE-saleor.txt.

def create_failed_transaction_event(
    event: TransactionEvent,
    cause: str,
):
    return TransactionEvent.objects.create(
        type=get_failed_type_based_on_event(event),
        amount_value=event.amount_value,
        currency=event.currency,
        transaction_id=event.transaction_id,
        message=cause,
        include_in_calculations=False,
        psp_reference=event.psp_reference,
    )

# ...

def _create_event_from_response(
    response: TransactionRequestEventResponse,
    app: App,
    transaction_id: int,
    currency: str,
) -> tuple[Optional[TransactionEvent], Optional[error_msg]]:
    app_identifier = None
    if app and app.identifier:
        app_identifier = app.identifier
    event = TransactionEvent(
        psp_reference=response.psp_reference,
        created_at=response.time or timezone.now(),
        type=response.type,
        amount_value=response.amount,
        external_url=response.external_url,
        currency=currency,
        transaction_id=transaction_id,
        message=response.message,
        app_identifier=app_identifier,
        app=app,
        include_in_calculations=True,
    )
    with transaction.atomic():
        event, error_msg = deduplicate_event(event, app)
        if error_msg:
            return None, error_msg
        if not event.pk:
            event.save()
    return event, None

# ...

def create_transaction_event_for_transaction_session(
    request_event: TransactionEvent,
    app: App,
    manager: "PluginsManager",
    discounts: Optional[Iterable["DiscountInfo"]],
    transaction_webhook_response: Optional[Dict[str, Any]] = None,
):
    request_event_type = "session-request"

    transaction_request_response, error_msg = _get_parsed_transaction_action_data(
        transaction_webhook_response=transaction_webhook_response,
        event_type=request_event_type,
        event_is_optional=False,
        psp_reference_is_optional=True,
    )
    if not transaction_request_response or not transaction_request_response.event:
        return create_failed_transaction_event(request_event, cause=error_msg or "")

    event = None
    request_event_update_fields = []
    response_event = transaction_request_response.event
    if not response_event.psp_reference and response_event.type not in [
        TransactionEventType.AUTHORIZATION_ACTION_REQUIRED,
        TransactionEventType.CHARGE_ACTION_REQUIRED,
    ]:
        return create_failed_transaction_event(
            request_event,
            cause=(
                f"Providing `pspReference` is required for "
                f"{response_event.type.upper()}"
            ),
        )
    elif response_event.type in [
        TransactionEventType.AUTHORIZATION_REQUEST,
        TransactionEventType.CHARGE_REQUEST,
    ]:
        request_event.type = response_event.type
        request_event.amount_value = response_event.amount
        request_event.psp_reference = response_event.psp_reference
        request_event.include_in_calculations = True
        request_event.app = app
        request_event_update_fields.extend(
            [
                "type",
                "amount_value",
                "psp_reference",
                "include_in_calculations",
                "app",
            ]
        )
        event = request_event
    else:
        event, error_message = _create_event_from_response(
            response_event,
            app=app,
            transaction_id=request_event.transaction_id,
            currency=request_event.currency,
        )
        if not event:
            return create_failed_transaction_event(
                request_event, cause=error_message or ""
            )
        request_event.psp_reference = event.psp_reference
        request_event_update_fields.append("psp_reference")
    if request_event_update_fields:
        request_event.save(update_fields=request_event_update_fields)

    if event.type in [
        TransactionEventType.AUTHORIZATION_REQUEST,
        TransactionEventType.AUTHORIZATION_SUCCESS,
        TransactionEventType.CHARGE_REQUEST,
        TransactionEventType.CHARGE_SUCCESS,
    ]:
        transaction_item = event.transaction
        previous_authorized_value = transaction_item.authorized_value
        previous_charged_value = transaction_item.charged_value

        transaction_item.psp_reference = event.psp_reference
        available_actions = transaction_request_response.available_actions
        if available_actions is not None:
            transaction_item.available_actions = list(set(available_actions))

        recalculate_transaction_amounts(transaction_item, save=False)
        transaction_item.save(
            update_fields=[
                "authorized_value",
                "charged_value",
                "refunded_value",
                "canceled_value",
                "authorize_pending_value",
                "charge_pending_value",
                "refund_pending_value",
                "cancel_pending_value",
                "psp_reference",
                "available_actions",
            ]
        )
        if transaction_item.order_id:
            # circular import
            from ..order.actions import order_transaction_updated

            update_order_with_transaction_details(transaction_item)
            order = cast(Order, transaction_item.order)
            order_info = fetch_order_info(order)
            order_transaction_updated(
                order_info=order_info,
                transaction_item=transaction_item,
                manager=manager,
                user=None,
                app=app,
                previous_authorized_value=previous_authorized_value,
                previous_charged_value=previous_charged_value,
            )
        elif transaction_item.checkout_id:
            transaction_amounts_for_checkout_updated(
                transaction_item, discounts, manager
            )
    return event


def create_transaction_event_from_request_and_webhook_response(
    request_event: TransactionEvent,
    app: App,
    transaction_webhook_response: Optional[Dict[str, Any]] = None,
):
    transaction_request_response, error_msg = _get_parsed_transaction_action_data(
        transaction_webhook_response=transaction_webhook_response,
        event_type=request_event.type,
    )
    if not transaction_request_response:
        return create_failed_transaction_event(request_event, cause=error_msg or "")

    psp_reference = transaction_request_response.psp_reference
    request_event.psp_reference = psp_reference
    request_event.save()
    event = None
    if response_event := transaction_request_response.event:
        event, error_msg = _create_event_from_response(
            response_event,
            app=app,
            transaction_id=request_event.transaction_id,
            currency=request_event.currency,
        )
        if error_msg:
            return create_failed_transaction_event(request_event, cause=error_msg)

    transaction_item = request_event.transaction
    previous_authorized_value = transaction_item.authorized_value
    previous_charged_value = transaction_item.charged_value

    recalculate_transaction_amounts(transaction_item, save=False)
    available_actions = transaction_request_response.available_actions
    if available_actions is not None:
        transaction_item.available_actions = list(set(available_actions))

    transaction_item.save(
        update_fields=[
            "available_actions",
            "authorized_value",
            "charged_value",
            "refunded_value",
            "canceled_value",
            "authorize_pending_value",
            "charge_pending_value",
            "refund_pending_value",
            "cancel_pending_value",
        ]
    )

    if transaction_item.order_id:
        # circular import
        from ..order.actions import order_transaction_updated

        manager = get_plugins_manager()
        order = cast(Order, transaction_item.order)
        order_info = fetch_order_info(order)
        update_order_with_transaction_details(transaction_item)
        order_transaction_updated(
            order_info=order_info,
            transaction_item=transaction_item,
            manager=manager,
            user=None,
            app=app,
            previous_authorized_value=previous_authorized_value,
            previous_charged_value=previous_charged_value,
        )
    elif transaction_item.checkout_id:
        discounts = fetch_active_discounts()
        manager = get_plugins_manager()
        transaction_amounts_for_checkout_updated(transaction_item, discounts, manager)
    return event
