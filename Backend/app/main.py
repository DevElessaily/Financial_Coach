from fastapi import FastAPI

from app.db.base import Base
from app.db.session import Engine

import app.models  # noqa: F401
from app.models import (  # noqa: F401
    alert,
    account,
    budget,
    category,
    category_mapping,
    currency_map,
    currency,
    notification,
    device_token,
    keyword,
    pending_category_review,
    pending_transaction,
    setting,
    sms,
    sms_regular_exp,
    sms_sender,
    transaction,
    user,
)

Base.metadata.create_all(bind=Engine)

from app.api.routes.pending_category import router as pending_category_router
from app.api.routes.sms_filter import router as sms_filter_router
from app.api.routes.transaction import router as transaction_router

app = FastAPI(title="FinalCode Backend")

app.include_router(pending_category_router)
app.include_router(sms_filter_router)
app.include_router(transaction_router)

from app.api.routes.alerts import router as alerts_router
from app.api.routes.categories import router as categories_router
from app.api.routes.category_mapping import router as category_mapping_router
from app.api.routes.currency import router as currency_router
from app.api.routes.currency_map import router as currency_map_router
from app.api.routes.notification import router as notification_router
from app.api.routes.pendingtransaction import router as pending_transaction_router
from app.api.routes.sms import router as sms_router
from app.api.routes.sms_regular_exp import router as sms_regular_exp_router
from app.api.routes.sms_sender import router as sms_sender_router
from app.api.routes.user import router as user_router

app.include_router(alerts_router)
app.include_router(categories_router)
app.include_router(category_mapping_router)
app.include_router(currency_router)
app.include_router(currency_map_router)
app.include_router(notification_router)
app.include_router(pending_transaction_router)
app.include_router(sms_router)
app.include_router(sms_regular_exp_router)
app.include_router(sms_sender_router)
app.include_router(user_router)
