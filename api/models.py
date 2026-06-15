"""
Pydantic models for API request/response validation.
"""

from typing import Any, Literal, Optional, Union
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DEFAULT_SITE_ID = "site_1"
MAX_SITE_ID_LENGTH = 80
MAX_CART_QUANTITY = 99
ACTION_SHOW_PRODUCTS = "SHOW_PRODUCTS"
ACTION_SHOW_COMPARISON = "SHOW_COMPARISON"
ACTION_FILTER_PRODUCTS = "FILTER_PRODUCTS"
ACTION_NAVIGATE_TO = "NAVIGATE_TO"
ACTION_SORT_PRODUCTS = "SORT_PRODUCTS"
ACTION_ADD_TO_CART = "ADD_TO_CART"
ACTION_REMOVE_FROM_CART = "REMOVE_FROM_CART"
ACTION_SHOW_PRODUCT_DETAIL = "SHOW_PRODUCT_DETAIL"
ACTION_CLEAR_FILTERS = "CLEAR_FILTERS"
ACTION_CLEAR_CART = "CLEAR_CART"
ACTION_CHECKOUT = "CHECKOUT"
ACTION_UPDATE_CART_QUANTITY = "UPDATE_CART_QUANTITY"
ACTION_CLEAR_HISTORY = "CLEAR_HISTORY"
ACTION_UPDATE_PREFERENCES = "UPDATE_PREFERENCES"
PRODUCT_IDS_PARAM = "product_ids"
PRODUCT_ID_PARAM = "product_id"
PAGE_PARAM = "page"
QUANTITY_PARAM = "quantity"
SORT_BY_PARAM = "sort_by"
SUPPORTED_SORT_KEYS = {"price_asc", "price_desc", "rating", "newest"}
PRODUCT_LIST_ACTIONS = {ACTION_SHOW_PRODUCTS, ACTION_SHOW_COMPARISON}
PRODUCT_ID_ACTIONS = {
    ACTION_ADD_TO_CART,
    ACTION_SHOW_PRODUCT_DETAIL,
    ACTION_UPDATE_CART_QUANTITY,
    ACTION_REMOVE_FROM_CART,
}
OPEN_PARAMETER_ACTIONS = {
    ACTION_FILTER_PRODUCTS,
    ACTION_CLEAR_FILTERS,
    ACTION_CLEAR_CART,
    ACTION_CHECKOUT,
    ACTION_CLEAR_HISTORY,
    ACTION_UPDATE_PREFERENCES,
}


class UIAction(BaseModel):
    action: Literal[
        ACTION_SHOW_PRODUCTS,
        ACTION_SHOW_COMPARISON,
        ACTION_FILTER_PRODUCTS,
        ACTION_NAVIGATE_TO,
        ACTION_SORT_PRODUCTS,
        ACTION_ADD_TO_CART,
        ACTION_REMOVE_FROM_CART,
        ACTION_SHOW_PRODUCT_DETAIL,
        ACTION_CLEAR_FILTERS,
        ACTION_CLEAR_CART,
        ACTION_CHECKOUT,
        ACTION_UPDATE_CART_QUANTITY,
        ACTION_CLEAR_HISTORY,
        ACTION_UPDATE_PREFERENCES,
    ] = Field(..., description="UI action type")
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_params(self) -> Self:
        params = self.params
        action = self.action

        if action in PRODUCT_LIST_ACTIONS:
            product_ids = params.get(PRODUCT_IDS_PARAM)
            if not isinstance(product_ids, list) or not all(
                isinstance(pid, (int, str)) for pid in product_ids
            ):
                raise ValueError(f"{action} requires product_ids: list[int|str]")
            return self

        if action in PRODUCT_ID_ACTIONS:
            if not isinstance(params.get(PRODUCT_ID_PARAM), (int, str)):
                raise ValueError(f"{action} requires product_id: int|str")
            return self

        if action == ACTION_NAVIGATE_TO:
            if not isinstance(params.get(PAGE_PARAM), str):
                raise ValueError("NAVIGATE_TO requires page: str")
            return self

        if action == ACTION_SORT_PRODUCTS:
            if params.get(SORT_BY_PARAM) not in SUPPORTED_SORT_KEYS:
                raise ValueError("SORT_PRODUCTS requires a supported sort_by value")
            return self

        if action in OPEN_PARAMETER_ACTIONS:
            return self

        return self


class CheckoutRequestItem(BaseModel):
    id: str
    name: str
    price: float = Field(ge=0)
    quantity: int = Field(ge=1, le=MAX_CART_QUANTITY)

class CheckoutRequest(BaseModel):
    site_id: str = Field(default=DEFAULT_SITE_ID, min_length=1, max_length=MAX_SITE_ID_LENGTH)
    address: str = "N/A"
    payment_method: str = "N/A"
    items: Optional[list[CheckoutRequestItem]] = None

class ShopResponse(BaseModel):
    transcript: str = Field(..., description="What the customer said")
    response_text: str = Field(..., description="Assistant's spoken response")
    intent: str = Field(..., description="Detected customer intent")
    confidence: float = Field(..., ge=0.0, le=1.0)
    ui_actions: list[UIAction] = Field(default_factory=list)
    audio_b64: str = Field("", description="Base64-encoded WAV audio")
    latency_ms: dict[str, float] = Field(default_factory=dict)

class ProductResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    brand: str
    category_name: str
    description: str
    price: float
    original_price: Optional[float] = None
    color: Optional[str] = None
    size_options: Optional[str] = None
    tags: Optional[str] = None
    rating: float
    review_count: int
    stock: int
    image_url: Optional[str] = None

    @field_validator("id", mode="before")
    @classmethod
    def serialize_id_as_string(cls, value: Any) -> str:
        return str(value)

class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    models: dict[str, str]

class AddToCartRequest(BaseModel):
    site_id: str = Field(default=DEFAULT_SITE_ID, min_length=1, max_length=MAX_SITE_ID_LENGTH)
    product_id: Union[int, str]
    quantity: int = Field(default=1, ge=1, le=MAX_CART_QUANTITY)


class CartItemResponse(ProductResponse):
    cart_id: int
    quantity: int
    added_at: str
