import os
from dotenv import load_dotenv
from app.db.session import engine
from app.db.base import Base
from app.models.tenant import Tenant
from app.models.user import User
from app.models.branch import Branch
load_dotenv()
target_metadata = Base.metadata
