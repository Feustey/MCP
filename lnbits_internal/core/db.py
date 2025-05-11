from lnbits_internal.core.models import CoreAppExtra
from lnbits_internal.db import Database

db = Database("database")
core_app_extra: CoreAppExtra = CoreAppExtra()
