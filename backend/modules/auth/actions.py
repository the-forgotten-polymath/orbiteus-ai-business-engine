"""Auth module — Action declarations for Command Palette."""
from orbiteus_core.ai import Action, ActionCategory

ACTIONS = [
    Action(
        id="auth.logout",
        label="Log Out",
        keywords=["logout", "log out", "sign out", "exit", "end session"],
        description="End session and go to login page",
        category=ActionCategory.EXECUTE,
        target="navigate",
        target_url="/login",
        icon="logout",
    ),
    Action(
        id="auth.profile",
        label="My Profile",
        keywords=["profile", "my account", "account settings", "my profile"],
        description="View and edit your user profile",
        category=ActionCategory.NAVIGATE,
        target="navigate",
        target_url="/profile",
        icon="user-circle",
    ),
]
