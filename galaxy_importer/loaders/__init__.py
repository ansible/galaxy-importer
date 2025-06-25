from .collection import (
    CollectionLoader,
)

from .legacy_role import (
    LegacyRoleLoader,
)

from .content import (
    ContentLoader,
    PluginLoader,
    ExtensionLoader,
    RoleLoader,
    PatternsLoader,
    get_loader_cls,
)

from .doc_string import (
    DocStringLoader,
)

__all__ = (
    "CollectionLoader",
    "ContentLoader",
    "DocStringLoader",
    "ExtensionLoader",
    "LegacyRoleLoader",
    "PatternsLoader",
    "PluginLoader",
    "RoleLoader",
    "get_loader_cls",
)
