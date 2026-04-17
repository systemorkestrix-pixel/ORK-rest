"""
Domain Event Types (Template)
"""

class EventTypes:
    # Orders
    ORDER_CREATED = "OrderCreated"
    ORDER_SENT_TO_KITCHEN = "OrderSentToKitchen"
    ORDER_READY = "OrderReady"
    ORDER_OUT_FOR_DELIVERY = "OrderOutForDelivery"
    ORDER_DELIVERED = "OrderDelivered"
    ORDER_CANCELED = "OrderCanceled"

    # Delivery
    DRIVER_ASSIGNED = "DriverAssigned"
    DRIVER_DEPARTED = "DriverDeparted"
    DELIVERY_COMPLETED = "DeliveryCompleted"
    DELIVERY_FAILED = "DeliveryFailed"
    DELIVERY_SETTLEMENT_CREATED = "DeliverySettlementCreated"

    # Inventory
    WAREHOUSE_INBOUND_POSTED = "WarehouseInboundPosted"
    WAREHOUSE_OUTBOUND_POSTED = "WarehouseOutboundPosted"
    WAREHOUSE_STOCK_COUNT_SETTLED = "WarehouseStockCountSettled"

    # Finance
    FINANCIAL_TRANSACTION_CREATED = "FinancialTransactionCreated"
    SHIFT_CLOSED = "ShiftClosed"
    EXPENSE_APPROVED = "ExpenseApproved"

    # Audit
    SYSTEM_AUDIT_RECORDED = "SystemAuditRecorded"
    SECURITY_AUDIT_RECORDED = "SecurityAuditRecorded"
