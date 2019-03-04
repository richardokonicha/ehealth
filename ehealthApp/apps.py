from django.apps import AppConfig


class EhealthappConfig(AppConfig):
    name = 'ehealthApp'

    def ready(self):
        import ehealthApp.signals
