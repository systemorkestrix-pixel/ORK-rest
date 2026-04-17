# Delivery Manual Address Plan

## Decision Lock

Date: `2026-03-22`

The delivery location strategy has changed.

We will no longer continue with an external location provider as the strategic path.

The approved path from now on is:

- manual delivery address management inside system settings
- public users see only approved delivery addresses
- country and currency are unified at the system-settings level
- delivery pricing is tied to manually managed hierarchical address nodes

This change is intended to keep the system closed, predictable, and free from external-provider burden.

## New Source of Truth

### 1. System Settings

The system-level source of truth becomes:

- `operating_country_code`
- `operating_country_name`
- `currency_code`
- `currency_name`
- `currency_symbol`
- `currency_decimal_places`

These settings must live in system settings, not inside delivery settings.

Reason:

- country affects the whole public and admin experience
- currency affects orders, finance, reports, public pages, and pricing
- delivery should consume these settings, not define them

### 2. Delivery Settings

Delivery settings become responsible for:

- manual hierarchical address nodes
- visibility to the public
- delivery coverage
- pricing per node
- active/inactive control
- sort order

## Global Hierarchical Address Model

We keep the international field semantics, but the values are managed manually:

1. `country`
2. `admin_area_level_1`
3. `admin_area_level_2`
4. `locality`
5. `sublocality`

Suggested data fields per node:

- `id`
- `parent_id`
- `level`
- `country_code`
- `code`
- `name`
- `display_name`
- `active`
- `visible_in_public`
- `sort_order`

Optional later:

- `postal_code`
- `notes`

## Public Experience Rule

The customer does not type a free-form delivery location.

The customer selects only from:

- available country context
- available admin areas
- available locality chain
- available visible public nodes

If a node is not published for the public, it does not appear.

## Pricing Rule

Pricing is no longer strategically tied to:

- external provider nodes

Pricing is tied to:

- internal manual hierarchical address nodes

Recommended pricing behavior:

- allow pricing on any node
- when the customer chooses a lower node, resolve the nearest priced ancestor

This gives flexibility:

- price by city
- price by district
- price by neighborhood

without forcing pricing on every leaf node.

## Reviewed Files And Impact

These modified backend areas were reviewed against the new direction:

- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/application/core_engine/domain/settings.py`
- `backend/application/operations_engine/domain/orders.py`
- `backend/app/orchestration/service_bridge.py`
- `backend/infrastructure/repositories/operations_repository.py`
- `backend/app/routers/public.py`
- `backend/app/routers/manager.py`
- `backend/application/operations_engine/domain/delivery_location_pricing.py`
- `backend/application/operations_engine/use_cases/*delivery*`
- `docs/archive/delivery_location_provider_strategy.md`

### Review Result

- The current provider-based work is technically stable.
- It should not be extended further as the long-term path.
- It should be treated as transitional work only.
- The next implementation path must pivot to manual address management.

## What We Keep

We keep these ideas:

- hierarchical address selection
- delivery pricing by location node
- storing a normalized location snapshot on the order
- public quote endpoint pattern

These are still correct and should remain part of the design.

## What We Stop

We stop building around:

- external provider dependency
- provider username configuration as the strategic base
- provider cache as the main source of delivery address nodes

## New Implementation Phases

### Phase A

Unify country and currency in system settings.

Close only when:

- country and currency are stored centrally
- delivery settings consume them instead of redefining them

#### Phase A Closure

Phase A was closed programmatically on `2026-03-22`.

Completed:

- added central system context settings for country and currency
- added manager API to read and update the central system context
- updated delivery settings output to consume the central system context
- verified backend type/lint/build gates
- verified runtime defaults and delivery-settings consumption

Locked result:

- delivery is no longer the owner of country or currency values
- country and currency now belong to system settings as the single source of truth

### Phase B

Add manual hierarchical delivery address nodes.

Close only when:

- manager can create, edit, disable, sort, and publish nodes
- nodes can be nested through the global hierarchy model

#### Phase B Closure

Phase B was closed programmatically on `2026-03-22`.

Completed:

- added a manual hierarchical address tree model
- added manager APIs for list/create/update of address nodes
- added public API for visible published nodes only
- enforced valid parent/child level progression
- bound all nodes to the centrally configured operating country
- verified migration, backend gates, frontend build, and runtime smoke behavior

Locked result:

- address hierarchy is now managed internally
- public delivery location selection can move forward without external provider dependency

### Phase C

Add delivery pricing rules on manual nodes.

Close only when:

- manager can assign a fee to a node
- public quote resolves the nearest valid priced node
- uncovered locations are rejected cleanly

#### Phase C Closure

Phase C was closed programmatically on `2026-03-22`.

Completed:

- tied delivery pricing rules to the internal manual address tree
- added manager APIs to list, save, delete, and preview pricing on address nodes
- updated public pricing quote to accept manual node selection directly
- implemented nearest-priced-ancestor resolution across the manual hierarchy
- preserved fixed-fee fallback only when no manual pricing rules exist at all
- verified backend gates and frontend build after the pivot

Locked result:

- delivery pricing is now owned by the manual address tree
- child nodes inherit the nearest priced parent automatically
- uncovered nodes are rejected cleanly once manual pricing is active

### Phase D

Wire the public order journey to manual selection.

Close only when:

- the customer selects from public nodes only
- the quote is shown from manual pricing
- the created order stores the normalized location snapshot

#### Phase D Closure

Phase D was closed programmatically on `2026-03-22`.

Completed:

- wired the public order journey to the manual hierarchical delivery nodes
- removed free-form delivery entry from the public checkout flow
- added public API client contracts for address-node loading and pricing quote
- made delivery checkout depend on a valid node selection and a successful quote
- sent the selected node key with the order payload while using the human-readable path as the delivery address label
- verified frontend build and backend gates after the integration

Locked result:

- public delivery orders now select their location only from approved published nodes
- delivery fees are quoted from the manual pricing tree before order creation
- order creation continues storing the normalized location snapshot through the existing backend pricing resolver

## Closure Rule

From this point on:

- no further phase should continue the external-provider strategy
- all next delivery-location work must reference this document
- if a file still contains provider-oriented logic, it must be treated as transitional and replaceable
