"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

# Auth-focused schemas
class AuthUser(BaseModel):
    email: EmailStr
    password_hash: str
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True

class Session(BaseModel):
    user_id: str
    token: str
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

# Demo request schema (for "Request a Demo" feature)
class DemoRequest(BaseModel):
    name: str = Field(..., description="Full name of requester")
    email: EmailStr
    school: Optional[str] = Field(None, description="School or organization name")
    message: Optional[str] = Field(None, description="Additional context or goals")
    preferred_time: Optional[str] = Field(None, description="Preferred time for demo call")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Example business schemas (kept for reference)
class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")
