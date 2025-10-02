from django import forms


class CarCostEstimationForm(forms.Form):
    OWNERSHIP_CHOICES = [
        ("cash", "Cash purchase"),
        ("finance", "Financed"),
        ("lease", "Leased"),
    ]

    FUEL_CHOICES = [
        ("gasoline", "Gasoline"),
        ("diesel", "Diesel"),
        ("electric", "Electric"),
        ("hybrid", "Hybrid"),
    ]

    country_code = forms.CharField(
        label="Country code",
        help_text="ISO country code such as US, CA, GB.",
        max_length=3,
    )
    region = forms.CharField(
        required=False,
        label="State/Province/Region",
        help_text="Optional region to refine regional tax and price lookups.",
    )
    currency_code = forms.CharField(
        label="Local currency",
        help_text="Currency ISO code such as USD or EUR.",
        max_length=3,
    )
    ownership_period_years = forms.IntegerField(
        label="Ownership period (years)",
        min_value=1,
        initial=5,
    )
    car_purchase_price = forms.DecimalField(
        label="Vehicle price",
        min_value=0,
        decimal_places=2,
        max_digits=12,
    )
    purchase_type = forms.ChoiceField(
        choices=OWNERSHIP_CHOICES,
        label="Acquisition method",
    )
    incentives_rebates = forms.DecimalField(
        label="Incentives or rebates",
        min_value=0,
        decimal_places=2,
        max_digits=12,
        required=False,
        initial=0,
        help_text="Any rebates, incentives, or credits that reduce the purchase price.",
    )
    local_tax_rate = forms.DecimalField(
        label="Local tax rate (%)",
        min_value=0,
        decimal_places=3,
        max_digits=6,
        help_text="Combined sales/VAT tax percentage applied to the purchase price.",
    )
    registration_fees_annual = forms.DecimalField(
        label="Registration & licensing (annual)",
        min_value=0,
        decimal_places=2,
        max_digits=10,
        initial=0,
        required=False,
    )
    insurance_cost_annual = forms.DecimalField(
        label="Insurance (annual)",
        min_value=0,
        decimal_places=2,
        max_digits=10,
    )
    maintenance_cost_annual = forms.DecimalField(
        label="Maintenance & wear (annual)",
        min_value=0,
        decimal_places=2,
        max_digits=10,
    )
    parking_cost_annual = forms.DecimalField(
        label="Parking or storage (annual)",
        min_value=0,
        decimal_places=2,
        max_digits=10,
        required=False,
        initial=0,
    )
    other_recurring_costs = forms.DecimalField(
        label="Other recurring costs (annual)",
        min_value=0,
        decimal_places=2,
        max_digits=10,
        required=False,
        initial=0,
    )
    annual_mileage = forms.IntegerField(
        label="Annual distance traveled (km)",
        min_value=0,
    )
    fuel_type = forms.ChoiceField(
        choices=FUEL_CHOICES,
        label="Primary energy type",
    )
    fuel_consumption_per_100km = forms.DecimalField(
        label="Fuel consumption per 100 km",
        decimal_places=2,
        max_digits=7,
        min_value=0,
        required=False,
        help_text="Liters per 100 km for combustion or hybrid vehicles.",
    )
    electricity_consumption_per_100km = forms.DecimalField(
        label="Electric consumption per 100 km",
        decimal_places=2,
        max_digits=7,
        min_value=0,
        required=False,
        help_text="kWh per 100 km for electric or plug-in hybrid vehicles.",
    )
    gas_price_per_liter = forms.DecimalField(
        label="Gasoline/Diesel price per liter",
        decimal_places=3,
        max_digits=7,
        min_value=0,
        required=False,
    )
    electricity_price_per_kwh = forms.DecimalField(
        label="Electricity price per kWh",
        decimal_places=4,
        max_digits=7,
        min_value=0,
        required=False,
    )
    finance_down_payment = forms.DecimalField(
        label="Down payment",
        decimal_places=2,
        max_digits=12,
        min_value=0,
        required=False,
    )
    finance_interest_rate = forms.DecimalField(
        label="Finance APR (%)",
        decimal_places=3,
        max_digits=6,
        min_value=0,
        required=False,
    )
    finance_term_months = forms.IntegerField(
        label="Finance term (months)",
        min_value=1,
        required=False,
    )
    lease_term_months = forms.IntegerField(
        label="Lease term (months)",
        min_value=1,
        required=False,
    )
    lease_monthly_payment = forms.DecimalField(
        label="Lease monthly payment",
        decimal_places=2,
        max_digits=10,
        min_value=0,
        required=False,
    )
    lease_drive_off_cost = forms.DecimalField(
        label="Lease drive-off cost",
        decimal_places=2,
        max_digits=10,
        min_value=0,
        required=False,
    )
    residual_value = forms.DecimalField(
        label="Expected resale/residual value at end",
        decimal_places=2,
        max_digits=12,
        min_value=0,
        required=False,
        help_text="Estimate of resale value for owned vehicles or residual obligation for leases.",
    )
    charging_installation_cost = forms.DecimalField(
        label="Home charger or infrastructure cost",
        decimal_places=2,
        max_digits=10,
        min_value=0,
        required=False,
        initial=0,
    )

    def clean(self):
        cleaned = super().clean()
        purchase_type = cleaned.get("purchase_type")

        if purchase_type == "finance":
            required_fields = [
                "finance_interest_rate",
                "finance_term_months",
            ]
            for field in required_fields:
                if not cleaned.get(field):
                    self.add_error(field, "This field is required for financed purchases.")
        elif purchase_type == "lease":
            required_fields = ["lease_term_months", "lease_monthly_payment"]
            for field in required_fields:
                if not cleaned.get(field):
                    self.add_error(field, "This field is required for leases.")

        fuel_type = cleaned.get("fuel_type")
        if fuel_type in {"gasoline", "diesel", "hybrid"} and not cleaned.get("fuel_consumption_per_100km"):
            self.add_error("fuel_consumption_per_100km", "Fuel consumption is required for combustion vehicles.")
        if fuel_type in {"electric", "hybrid"} and not cleaned.get("electricity_consumption_per_100km"):
            self.add_error(
                "electricity_consumption_per_100km",
                "Electric consumption is required for electric or plug-in hybrid vehicles.",
            )

        for code_field in ["country_code", "currency_code"]:
            if cleaned.get(code_field):
                cleaned[code_field] = cleaned[code_field].upper()

        return cleaned

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
                continue
            base_class = "form-control"
            if isinstance(widget, (forms.Select, forms.SelectMultiple)):
                base_class = "form-select"
            widget.attrs.setdefault("class", base_class)
