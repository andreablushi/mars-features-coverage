"""Selection: the operations that narrow catalogs, records, and fields."""

from download.selection.dedupe import dedupe
from download.selection.features import select_features
from download.selection.fields import retain_fields

__all__ = ["dedupe", "retain_fields", "select_features"]
