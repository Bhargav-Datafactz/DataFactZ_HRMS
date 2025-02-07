from django.apps import AppConfig

from datafactz_automations.signals import start_automation


class DatafactzAutomationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "datafactz_automations"

    def ready(self) -> None:
        ready = super().ready()
        try:

            from base.templatetags.datafactzfilters import app_installed
            from employee.models import Employee
            from datafactz_automations.methods.methods import get_related_models
            from datafactz_automations.models import MODEL_CHOICES

            recruitment_installed = False
            if app_installed("recruitment"):
                recruitment_installed = True

            models = [Employee]
            if recruitment_installed:
                from recruitment.models import Candidate

                models.append(Candidate)

            main_models = models
            for main_model in main_models:
                related_models = get_related_models(main_model)

                for model in related_models:
                    path = f"{model.__module__}.{model.__name__}"
                    MODEL_CHOICES.append((path, model.__name__))
            MODEL_CHOICES.append(("employee.models.Employee", "Employee"))
            MODEL_CHOICES = list(set(MODEL_CHOICES))
            try:
                start_automation()
            except:
                """
                Migrations are not affected yet
                """
        except:
            """
            Models not ready yet
            """
        return ready
