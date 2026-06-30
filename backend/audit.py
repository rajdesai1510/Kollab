"""
Quick audit script — checks every import layer of the Nexus backend.
Run from: d:\startup\backend\
Command:  python audit.py
"""
import sys
import os

sys.path.insert(0, ".")

# Mock required env vars so pydantic-settings doesn't abort
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/1")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-32-chars-minimum!!")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test")
os.environ.setdefault("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
os.environ.setdefault("INSTAGRAM_APP_ID", "test")
os.environ.setdefault("INSTAGRAM_APP_SECRET", "test")
os.environ.setdefault("INSTAGRAM_REDIRECT_URI", "http://localhost:8000/api/auth/instagram/callback")
os.environ.setdefault("ENCRYPTION_KEY", "Cm6ULlGVFk6w_VmlFMmBMoLV0rC_G0P-eGYMKYJP2OY=")

PASS = "[OK]  "
FAIL = "[FAIL]"
results = []


def check(label, fn):
    try:
        result = fn()
        msg = f"{PASS} {label}"
        if result:
            msg += f" — {result}"
        print(msg)
        results.append((True, label))
        return True
    except Exception as e:
        import traceback
        print(f"{FAIL} {label}: {e}")
        traceback.print_exc()
        results.append((False, label, str(e)))
        return False


print("\n" + "=" * 60)
print("  Nexus Backend — Import Chain Audit")
print("=" * 60 + "\n")

print("[ Config ]\n")
ok = check("app.config.settings", lambda: __import__("app.config", fromlist=["settings"]).settings.APP_ENV.value)
if not ok:
    print("\nConfig failed — cannot continue.\n")
    sys.exit(1)

print("\n[ Core Infrastructure ]\n")
check("core.logger", lambda: __import__("app.core.logger", fromlist=["logger"]) and "CollabLogger loaded")
check("core.jwt_manager", lambda: __import__("app.core.jwt_manager", fromlist=["jwt_manager"]) and "JWTManager loaded")
check("core.encryption", lambda: __import__("app.core.encryption", fromlist=["encryption_manager"]) and "EncryptionManager loaded")
check("core.database", lambda: __import__("app.core.database", fromlist=["db_manager"]) and "DatabaseManager loaded")

print("\n[ Middleware ]\n")
check(
    "middleware.auth_middleware (AuthMiddleware + aliases)",
    lambda: (
        __import__("app.middleware.auth_middleware", fromlist=["auth_middleware", "get_current_user", "require_role"])
        and "auth_middleware, get_current_user, require_role loaded"
    ),
)

print("\n[ Models (Beanie Documents) ]\n")
check("models.user", lambda: __import__("app.models.user", fromlist=["User", "UserRole"]) and "User, UserRole")
check("models.brand_profile", lambda: __import__("app.models.brand_profile", fromlist=["BrandProfile"]) and "BrandProfile")
check("models.creator_profile", lambda: __import__("app.models.creator_profile", fromlist=["CreatorProfile"]) and "CreatorProfile")
check("models.campaign", lambda: __import__("app.models.campaign", fromlist=["Campaign"]) and "Campaign")
check("models.connection", lambda: __import__("app.models.connection", fromlist=["Connection"]) and "Connection")
check("models.message", lambda: __import__("app.models.message", fromlist=["Message"]) and "Message")
check("models.notification", lambda: __import__("app.models.notification", fromlist=["Notification"]) and "Notification")

print("\n[ Schemas ]\n")
check("schemas.auth", lambda: __import__("app.schemas.auth", fromlist=["AuthResponse"]) and "AuthResponse, UserResponse")
check("schemas.brand", lambda: __import__("app.schemas.brand", fromlist=["BrandCreateRequest"]) and "BrandCreateRequest, BrandProfileResponse")
check("schemas.creator", lambda: __import__("app.schemas.creator", fromlist=["CreatorProfileResponse"]) and "CreatorProfileResponse")
check("schemas.notification", lambda: __import__("app.schemas.notification", fromlist=["NotificationResponse"]) and "NotificationResponse")
check("schemas.shared", lambda: __import__("app.schemas.shared", fromlist=["CampaignResponse"]) and "CampaignResponse, ConnectionResponse, MessageResponse")

print("\n[ Services ]\n")
check("services.auth_service", lambda: __import__("app.services.auth_service", fromlist=["AuthService"]) and "AuthService")
check("services.creator_service", lambda: __import__("app.services.creator_service", fromlist=["CreatorService"]) and "CreatorService")
check("services.connection_service", lambda: __import__("app.services.connection_service", fromlist=["ConnectionService"]) and "ConnectionService")
check("services.notification_service", lambda: __import__("app.services.notification_service", fromlist=["NotificationService"]) and "NotificationService")
check("services.instagram_service", lambda: __import__("app.services.instagram_service", fromlist=["InstagramService"]) and "InstagramService")

print("\n[ Tasks ]\n")
check("tasks.celery_app", lambda: __import__("app.tasks.celery_app", fromlist=["celery_app"]) and "CeleryAppFactory + celery_app")
check("tasks.instagram_sync", lambda: __import__("app.tasks.instagram_sync", fromlist=["instagram_sync_task"]) and "InstagramSyncTask loaded")

print("\n[ Routers (Class-based) ]\n")


def check_router(module, attr):
    mod = __import__(f"app.routers.{module}", fromlist=[attr])
    router_obj = getattr(mod, attr)
    count = len(router_obj.router.routes)
    return f"{count} routes registered"


check("routers.auth (AuthRouter)", lambda: check_router("auth", "auth_router"))
check("routers.creators (CreatorRouter)", lambda: check_router("creators", "creator_router"))
check("routers.brands (BrandRouter)", lambda: check_router("brands", "brand_router"))
check("routers.campaigns (CampaignRouter)", lambda: check_router("campaigns", "campaign_router"))
check("routers.connections (ConnectionRouter)", lambda: check_router("connections", "connection_router"))
check("routers.messages (MessageRouter)", lambda: check_router("messages", "message_router"))
check("routers.notifications (NotificationRouter)", lambda: check_router("notifications", "notification_router"))
check("routers.admin (AdminRouter)", lambda: check_router("admin", "admin_router"))

print("\n[ Application (main.py) ]\n")


def check_app():
    from app.main import app
    api_routes = [r for r in app.routes if hasattr(r, "path") and r.path.startswith("/api")]
    return f"{len(api_routes)} API routes mounted"


check("main.app (FastAPI instance)", check_app)

# Full route table
print("\n[ Full Route Table ]\n")
try:
    from app.main import app

    for route in sorted(app.routes, key=lambda r: getattr(r, "path", "")):
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", None)
        if methods:
            for m in sorted(methods):
                if m != "HEAD":
                    print(f"  {m:7} {path}")
        elif path:
            print(f"  WS      {path}")
except Exception as e:
    print(f"  Could not list routes: {e}")

# Summary
print("\n" + "=" * 60)
passed = sum(1 for r in results if r[0])
failed = sum(1 for r in results if not r[0])
print(f"  RESULT: {passed} passed, {failed} failed")
if failed:
    print("\n  FAILURES:")
    for r in results:
        if not r[0]:
            print(f"    - {r[1]}: {r[2]}")
    sys.exit(1)
else:
    print("  All import checks passed. Backend is structurally sound.")
print("=" * 60 + "\n")
