# Database interface for Karim/Ahmed

Pranav/Cam provide storage. Karim/Ahmed own the equipment form, catalog, and Flask
handlers that call this interface. Use one initialized database path throughout
the shared app; do not point routes at separate sample files.

## Initialize once

```python
from campusgear.db import initialize
initialize()
```

Default file: `instance/campusgear.sqlite3`, relative to this repository, not the
terminal location. `initialize(path)` and `transaction(path)` accept an alternative
shared path. Initialization preserves rows; it does not migrate existing tables.

## Equipment fields

| Field | Meaning/default |
| --- | --- |
| id | Automatically assigned internal numeric ID |
| asset_id | Required unique inventory label, e.g. KU-003 |
| name | Required nonblank equipment name |
| category | Required nonblank category |
| description | Required text; form should require a useful description |
| condition | Defaults to good |
| status | Defaults to available; allowed: available, reserved, checked_out, maintenance |

## Registration handler: save submitted fields

Validate/trim the form fields first, then call:

```python
from campusgear.db import transaction, insert_record, list_equipment

with transaction() as connection:
    item_id = insert_record(connection, 'equipment',
                            name=name, category=category,
                            description=description, asset_id=asset_id)
```

`insert_record` returns the new ID. The transaction commits on success and rolls
back on error. Catch `sqlite3.IntegrityError` outside the `with` block and show an
appropriate form error (including duplicate asset IDs); do not treat every error
as a duplicate. Unknown table/field names raise ValueError. SQL values are bound
using placeholders. Do not pass arbitrary browser-selected field/table names.

## Catalog handler: read records

```python
with transaction() as connection:
    equipment = list_equipment(connection, available_only=True)
```

Returns a list of dictionaries with the fields above, ordered by ID. Omit
`available_only=True` for all items and display their saved status correctly.
This is current status, not a reservation-date availability calculation.
`get_record(connection, 'equipment', item_id)` returns one dictionary or None.

## What to send back when ready

Only the branch/files, how to run them, and form/catalog route names. Pranav/Cam
will use those names for the role-specific links and help connect the shared DB.
Proposed combined check: add an item → refresh catalog → item appears; duplicate
asset ID → clear error without another row. No login needed for the TA preview.
