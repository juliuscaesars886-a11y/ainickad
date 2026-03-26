from django.apps import AppConfig


class StaffConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'staff'
    
    def ready(self):
        """
        Import signal handlers when the app is ready.
        This ensures signals are registered and active.
        """
        import staff.signals  # noqa: F401
