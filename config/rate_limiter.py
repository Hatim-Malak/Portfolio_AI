from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize it here once
limiter = Limiter(key_func=get_remote_address)