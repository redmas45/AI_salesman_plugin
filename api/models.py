"""
Pydantic models for API request/response validation.
"""

from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UIAction(BaseModel):
    action: Literal[
        "SHOW_PRODUCTS",
        "SHOW_COMPARISON",
        "FILTER_PRODUCTS",
        "NAVIGATE_TO",
        "SORT_PRODUCTS",
        "ADD_TO_CART",
        "REMOVE_FROM_CART",
        "SHOW_PRODUCT_DETAIL",
        "CLEAR_FILTERS",
        "CLEAR_CART",
        "CHECKOUT",
        "UPDATE_CART_QUANTITY",
        "CLEAR_HISTORY",
        "UPDATE_PREFERENCES",
    ] = Field(..., description="UI action type")
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_params(self):
        params = self.params
        action = self.action

        if action in ("SHOW_PRODUCTS", "SHOW_COMPARISON"):
            product_ids = params.get("product_ids")
            if not isinstance(product_ids, list) or not all(
                isinstance(pid, (int, str)) for pid in product_ids
            ):
                raise ValueError(f"{action} requires product_ids: list[int|str]")

        elif action in ("ADD_TO_CART", "SHOW_PRODUCT_DETAIL", "UPDATE_CART_QUANTITY"):
            if not isinstance(params.get("product_id"), (int, str)):
                raise ValueError(f"{action} requires product_id: int|str")

        elif action == "FILTER_PRODUCTS":
            # Allow any filter params as we handle unsupported ones gracefully
            pass

        elif action == "NAVIGATE_TO":
            if not isinstance(params.get("page"), str):
                raise ValueError("NAVIGATE_TO requires page: str")

        elif action == "SORT_PRODUCTS":
            if params.get("sort_by") not in {
                "price_asc",
                "price_desc",
                "rating",
                "newest",
            }:
                raise ValueError("SORT_PRODUCTS requires a supported sort_by value")

        elif action == "CLEAR_FILTERS":
            pass

        elif action == "CLEAR_CART":
            pass

        elif action == "REMOVE_FROM_CART":
            if not isinstance(params.get("product_id"), (int, str)):
                raise ValueError("REMOVE_FROM_CART requires product_id: int|str")

        elif action == "CHECKOUT":
            pass  # No strict parameter requirements

        return self


class CheckoutRequest(BaseModel):
    site_id: str = "site_1"
    address: str = "N/A"
    payment_method: str = "N/A"

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
    site_id: str = "site_1"
    product_id: Union[int, str]
    quantity: int = Field(default=1, ge=1, le=99)


class CartItemResponse(ProductResponse):
    cart_id: int
    quantity: int
    added_at: str
