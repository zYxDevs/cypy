import sys as _sys
from typing import Any as _Any, Dict as _Dict, TypeAlias as _TA

if _sys.version_info >= (3, 11):
    from typing import Never as _Never
    Never: _TA = _Never
else:
    from typing import NoReturn as _NoReturn
    Never: _TA = _NoReturn

AnyDict: _TA = _Dict[str, _Any]
APIKey: _TA = str
