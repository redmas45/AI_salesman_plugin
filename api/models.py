"""
Pydantic models for API request/response validation.
"""

from typing import Any, Optional, Union
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from agent.actions.registry import is_supported_action, normalize_action_name

DEFAULT_SITE_ID = "site_1"
MAX_SITE_ID_LENGTH = 80
MAX_CART_QUANTITY = 99
ACTION_SHOW_PRODUCTS = "SHOW_PRODUCTS"
ACTION_SHOW_COMPARISON = "SHOW_COMPARISON"
ACTION_SHOW_ENTITIES = "SHOW_ENTITIES"
ACTION_COMPARE_ENTITIES = "COMPARE_ENTITIES"
ACTION_FILTER_PRODUCTS = "FILTER_PRODUCTS"
ACTION_NAVIGATE_TO = "NAVIGATE_TO"
ACTION_OPEN_ENTITY_DETAIL = "OPEN_ENTITY_DETAIL"
ACTION_SORT_ENTITIES = "SORT_ENTITIES"
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
ACTION_RUN_DOM_SEQUENCE = "RUN_DOM_SEQUENCE"
PRODUCT_IDS_PARAM = "product_ids"
PRODUCT_ID_PARAM = "product_id"
ENTITY_IDS_PARAM = "entity_ids"
ENTITY_ID_PARAM = "entity_id"
PAGE_PARAM = "page"
QUANTITY_PARAM = "quantity"
SORT_BY_PARAM = "sort_by"
SUPPORTED_SORT_KEYS = {"price_asc", "price_desc", "rating", "newest"}
PRODUCT_LIST_ACTIONS = {ACTION_SHOW_PRODUCTS, ACTION_SHOW_COMPARISON}
ENTITY_LIST_ACTIONS = {ACTION_SHOW_ENTITIES, ACTION_COMPARE_ENTITIES}
PRODUCT_ID_ACTIONS = {
    ACTION_ADD_TO_CART,
    ACTION_SHOW_PRODUCT_DETAIL,
    ACTION_UPDATE_CART_QUANTITY,
    ACTION_REMOVE_FROM_CART,
}
ENTITY_ID_ACTIONS = {ACTION_OPEN_ENTITY_DETAIL}
OPEN_PARAMETER_ACTIONS = {
    ACTION_FILTER_PRODUCTS,
    ACTION_CLEAR_FILTERS,
    ACTION_CLEAR_CART,
    ACTION_CHECKOUT,
    ACTION_CLEAR_HISTORY,
    ACTION_UPDATE_PREFERENCES,
    ACTION_RUN_DOM_SEQUENCE,
}


class UIAction(BaseModel):
    action: str = Field(..., description="UI action type")
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_params(self) -> Self:
        params = self.params
        action = normalize_action_name(self.action)
        if not is_supported_action(action):
            raise ValueError(f"Unsupported UI action: {self.action}")
        self.action = action

        if action in PRODUCT_LIST_ACTIONS:
            product_ids = params.get(PRODUCT_IDS_PARAM)
            if not isinstance(product_ids, list) or not all(
                isinstance(pid, (int, str)) for pid in product_ids
            ):
                raise ValueError(f"{action} requires product_ids: list[int|str]")
            return self

        if action in ENTITY_LIST_ACTIONS:
            entity_ids = params.get(ENTITY_IDS_PARAM)
            if not isinstance(entity_ids, list) or not all(
                isinstance(entity_id, (int, str)) for entity_id in entity_ids
            ):
                raise ValueError(f"{action} requires entity_ids: list[int|str]")
            return self

        if action in PRODUCT_ID_ACTIONS:
            if not isinstance(params.get(PRODUCT_ID_PARAM), (int, str)):
                raise ValueError(f"{action} requires product_id: int|str")
            return self

        if action in ENTITY_ID_ACTIONS:
            if not isinstance(params.get(ENTITY_ID_PARAM), (int, str)):
                raise ValueError(f"{action} requires entity_id: int|str")
            return self

        if action == ACTION_NAVIGATE_TO:
            if not isinstance(params.get(PAGE_PARAM), str):
                raise ValueError("NAVIGATE_TO requires page: str")
            return self

        if action in {ACTION_SORT_PRODUCTS, ACTION_SORT_ENTITIES}:
            if params.get(SORT_BY_PARAM) not in SUPPORTED_SORT_KEYS:
                raise ValueError(f"{action} requires a supported sort_by value")
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
    retrieval: dict[str, Any] = Field(
        default_factory=dict,
        description="Compact retrieval diagnostics for CRM/runtime debugging",
    )

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


class KnowledgeItemResponse(BaseModel):
    """Public, widget-safe knowledge item shape."""

    model_config = ConfigDict(extra="ignore")

    id: str
    external_id: str = ""
    entity_type: str
    title: str
    subtitle: str = ""
    summary: str = ""
    body: str = ""
    url: str = ""
    image_url: str = ""
    attributes: Any = Field(default_factory=dict)
    pricing: Any = Field(default_factory=dict)
    availability: Any = Field(default_factory=dict)
    location: Any = Field(default_factory=dict)
    contact: Any = Field(default_factory=dict)
    policy: Any = Field(default_factory=dict)
    risk_tags: Any = Field(default_factory=list)

    @field_validator("id", "external_id", mode="before")
    @classmethod
    def serialize_string_ids(cls, value: Any) -> str:
        return str(value or "")

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


class VariantResponse(BaseModel):
    """Response model for product variants."""
    model_config = ConfigDict(extra="ignore")

    id: str
    product_id: str
    sku: Optional[str] = None
    title: str
    option1_name: Optional[str] = None
    option1_value: Optional[str] = None
    option2_name: Optional[str] = None
    option2_value: Optional[str] = None
    option3_name: Optional[str] = None
    option3_value: Optional[str] = None
    price: float
    compare_at_price: Optional[float] = None
    stock: int = 0
    available: bool = True
    image_url: Optional[str] = None
    cart_id: Optional[str] = None

    @field_validator("id", "product_id", mode="before")
    @classmethod
    def serialize_ids_as_string(cls, value: Any) -> str:
        return str(value)
