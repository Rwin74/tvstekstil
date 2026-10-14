from firma.app import create_app
from firma.config import Settings
from firma.site_auth import AdminGateway
from firma.site_store import SupabaseStore

settings = Settings.from_env()
settings.cloud = True
app = AdminGateway(create_app(settings, site_store=SupabaseStore()))
