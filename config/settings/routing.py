import environ

env = environ.Env()

ROUTING_API_KEY = env("ROUTING_API_KEY", default="")
ROUTING_API_URL = env(
    "ROUTING_API_URL",
    default="https://api.openrouteservice.org",
)
