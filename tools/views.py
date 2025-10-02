from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import FormView

from .forms import CarCostEstimationForm
from .services import estimate_car_cost, gather_suggested_data


class CarCostEstimatorView(LoginRequiredMixin, FormView):
    template_name = "tools/car_cost_estimator.html"
    form_class = CarCostEstimationForm
    success_url = reverse_lazy("car_cost_estimator")
    login_url = reverse_lazy("account_login")

    def dispatch(self, request, *args, **kwargs):
        self.country = request.GET.get("country", "US")
        self.region = request.GET.get("region")
        self.suggested_data = gather_suggested_data(self.country, self.region)
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        initial.setdefault("country_code", self.country)
        if self.suggested_data.currency_code:
            initial.setdefault("currency_code", self.suggested_data.currency_code)
        if self.suggested_data.fuel_price_per_liter:
            initial.setdefault("gas_price_per_liter", self.suggested_data.fuel_price_per_liter)
        if self.suggested_data.electricity_price_per_kwh:
            initial.setdefault(
                "electricity_price_per_kwh", self.suggested_data.electricity_price_per_kwh
            )
        if self.suggested_data.tax_rate_percent:
            initial.setdefault("local_tax_rate", self.suggested_data.tax_rate_percent)
        initial.setdefault("local_tax_rate", 0)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["suggested_data"] = self.suggested_data
        context["country"] = self.country
        context["region"] = self.region
        return context

    def form_valid(self, form):
        cleaned = form.cleaned_data.copy()
        if not cleaned.get("gas_price_per_liter") and self.suggested_data.fuel_price_per_liter:
            cleaned["gas_price_per_liter"] = self.suggested_data.fuel_price_per_liter
            messages.info(self.request, "Applied suggested local fuel price from available data.")
        if (
            not cleaned.get("electricity_price_per_kwh")
            and self.suggested_data.electricity_price_per_kwh
        ):
            cleaned["electricity_price_per_kwh"] = self.suggested_data.electricity_price_per_kwh
            messages.info(
                self.request,
                "Applied suggested local electricity price from available data.",
            )
        if not cleaned.get("local_tax_rate") and self.suggested_data.tax_rate_percent:
            cleaned["local_tax_rate"] = self.suggested_data.tax_rate_percent
            messages.info(
                self.request,
                "Applied suggested local tax rate from available data.",
            )

        results = estimate_car_cost(cleaned)
        context = self.get_context_data(form=form, results=results)
        return self.render_to_response(context)
