from enum import StrEnum


class UserRole(StrEnum):
    MANAGER = "manager"
    KITCHEN = "kitchen"
    DELIVERY = "delivery"


class OrderType(StrEnum):
    DINE_IN = "dine-in"
    TAKEAWAY = "takeaway"
    DELIVERY = "delivery"


class OrderStatus(StrEnum):
    CREATED = "CREATED"
    CONFIRMED = "CONFIRMED"
    SENT_TO_KITCHEN = "SENT_TO_KITCHEN"
    IN_PREPARATION = "IN_PREPARATION"
    READY = "READY"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    DELIVERY_FAILED = "DELIVERY_FAILED"
    CANCELED = "CANCELED"


class TableStatus(StrEnum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    RESERVED = "reserved"


class ProductKind(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    # Legacy aliases kept to avoid breaking older imports while transport
    # layers are migrated in the next frontend phase.
    SELLABLE = "primary"
    INTERNAL = "secondary"


class ResourceScope(StrEnum):
    KITCHEN = "kitchen"
    STOCK = "stock"


class PaymentStatus(StrEnum):
    UNPAID = "unpaid"
    PAID = "paid"
    REFUNDED = "refunded"


class CollectionChannel(StrEnum):
    CASHIER = "cashier"
    DRIVER = "driver"
    ONLINE = "online"


class FinancialTransactionType(StrEnum):
    SALE = "sale"
    REFUND = "refund"
    EXPENSE = "expense"
    FOOD_REVENUE = "food_revenue"
    DELIVERY_REVENUE = "delivery_revenue"
    DRIVER_PAYABLE = "driver_payable"
    COLLECTION_CLEARING = "collection_clearing"
    COLLECTION_ADJUSTMENT = "collection_adjustment"
    REFUND_FOOD_REVENUE = "refund_food_revenue"
    REFUND_DELIVERY_REVENUE = "refund_delivery_revenue"
    REVERSE_DRIVER_PAYABLE = "reverse_driver_payable"
    REVERSE_COLLECTION_CLEARING = "reverse_collection_clearing"


class FinancialTransactionDirection(StrEnum):
    DEBIT = "debit"
    CREDIT = "credit"


class ResourceMovementType(StrEnum):
    ADD = "add"
    DEDUCT = "deduct"
    ADJUST = "adjust"


class DriverStatus(StrEnum):
    AVAILABLE = "available"
    BUSY = "busy"
    INACTIVE = "inactive"


class DeliveryAssignmentStatus(StrEnum):
    NOTIFIED = "notified"
    ASSIGNED = "assigned"
    DEPARTED = "departed"
    DELIVERED = "delivered"
    FAILED = "failed"


class DeliveryDispatchStatus(StrEnum):
    OFFERED = "offered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELED = "canceled"


class DeliveryDispatchScope(StrEnum):
    DRIVER = "driver"
    PROVIDER = "provider"


class DeliverySettlementStatus(StrEnum):
    PENDING = "pending"
    PARTIALLY_REMITTED = "partially_remitted"
    REMITTED = "remitted"
    SETTLED = "settled"
    VARIANCE = "variance"
    REVERSED = "reversed"


class DriverShareModel(StrEnum):
    FULL_DELIVERY_FEE = "full_delivery_fee"
    FIXED_AMOUNT = "fixed_amount"
    PERCENTAGE = "percentage"


class CashboxMovementType(StrEnum):
    DRIVER_REMITTANCE = "driver_remittance"
    DRIVER_PAYOUT = "driver_payout"
    CASH_ORDER_COLLECTION = "cash_order_collection"
    CASH_REFUND = "cash_refund"
    CASH_ADJUSTMENT = "cash_adjustment"


class CashboxMovementDirection(StrEnum):
    IN = "in"
    OUT = "out"


class CashChannel(StrEnum):
    CASH_DRAWER = "cash_drawer"
    SAFE = "safe"
    BANK = "bank"
    WALLET = "wallet"
