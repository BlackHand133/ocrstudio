"""Shared helpers for scripts that derive a new workspace version file.

A version file carries its own header — description, parent_version, timestamps
— and the app shows those in the version menu. A script that copies the source
JSON and edits only the annotations leaves that header describing the *source*,
so the new version appears in the UI under its ancestor's name and date.

Both derive-a-version scripts need the same two pieces, so they live here rather
than in each of them.
"""

from datetime import datetime


def next_version_path(workspace_dir):
    """Next version number above the highest already in use.

    Not the lowest free one: a workspace holding v1 and v4 would get a "v2"
    containing data derived from v4, which reads as older than its own source.
    """
    highest = 0
    for path in workspace_dir.glob("v*.json"):
        stem = path.stem
        if stem.startswith("v") and stem[1:].isdigit():
            highest = max(highest, int(stem[1:]))
    return workspace_dir / f"v{highest + 1}.json"


def stamp_version(data, source_version, description, **metadata):
    """Rewrite the copied header so it describes this version, not its parent.

    Without this the new file inherits the source's description and created_at
    and shows up in the app's version menu labelled as the version it came from.

    Args:
        data: the loaded version dict, modified in place
        source_version: name of the version this was derived from
        description: what this derivation did, shown in the UI
        **metadata: extra counters to record under ``metadata``
    """
    now = datetime.now().isoformat(timespec="seconds")
    data["description"] = description
    data["parent_version"] = source_version
    data["created_at"] = now
    data["modified_at"] = now
    meta = data.setdefault("metadata", {})
    meta["derived_from"] = source_version
    meta["generated_at"] = now
    meta.update(metadata)
    return data
