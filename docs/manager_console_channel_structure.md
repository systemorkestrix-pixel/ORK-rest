# Manager Console Channel Structure

Date: `2026-04-05`

Status: `Authoritative`

This document closes the channel naming decision for the Manager Console.

## Final rule

- `Restaurant` is no longer an independent Manager channel.
- `Menu` is now an `Operations` section.
- `Operating Expenses` return to `Finance` as their visible home.

## Manager Console channels

### Operations

- Orders
- Tables
- Menu

Capabilities:

- `core_ops`
- `core_menu`

Notes:

- `Menu` is managed here because it is part of the daily operating surface seen by the manager.
- There is no separate `Restaurant` channel in the Manager Console anymore.
- `Menu` follows the same UI reference used by `Orders` and `Tables` inside Operations.

### Kitchen

- Kitchen Monitor
- Kitchen Settings

Capability:

- `kitchen_module`

### Delivery

- Drivers
- Delivery Settings
- Delivery Tracking

Capabilities:

- `delivery_management`
- `delivery_execution`

### Warehouse

- Stock Ledger
- Vouchers
- Suppliers

Capability:

- `warehouse_module`

### Finance

- Overview
- Expenses
- Cashbox
- Settlements
- Entries
- Closures

Capability:

- `finance_module`

Notes:

- `Expenses` are owned by finance again.
- If a simplified operating expense tool appears elsewhere in the future, finance remains the source of truth.

### Intelligence

- Operational Heart
- Reports

Capability:

- `reports_module`

### System

- Users
- Roles
- Settings
- Audit

Capabilities:

- `advanced_permissions`
- `audit_module`

## Routing rule

- `/console/operations/menu` is the canonical menu route.
- Old restaurant paths must redirect:
  - `/console/restaurant`
  - `/console/restaurant/menu`
  - `/console/restaurant/settings`
- Old restaurant expense path must redirect to:
  - `/console/finance/expenses`

## UI rule

- Do not use `Restaurant` as a visible Manager channel label from now on.
- Use `Menu` as an `Operations` section label.
- Use `Expenses` only under `Finance`.

## Why this is the stable base

- It keeps the Manager Console aligned with plan-based capability toggling.
- It removes the artificial split between operations and menu work.
- It keeps finance ownership clear while preserving future product packaging flexibility.
