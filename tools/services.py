from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from typing import Dict, Optional

import requests

API_NINJAS_KEY = os.getenv("API_NINJAS_KEY")
RESTCOUNTRIES_URL = "https://restcountries.com/v3.1/alpha/{code}"
EIA_GAS_PRICE_URL = (
    "https://api.eia.gov/series/?api_key=DEMO_KEY&series_id=PET.EMM_EPM0_PTE_NUS_DPG.W"
)


@dataclass
class SuggestedData:
    currency_code: Optional[str] = None
    fuel_price_per_liter: Optional[Decimal] = None
    electricity_price_per_kwh: Optional[Decimal] = None
    tax_rate_percent: Optional[Decimal] = None


def _safe_decimal(value: Optional[float | str | Decimal]) -> Decimal:
    if value in (None, "", 0):
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@lru_cache(maxsize=64)
def fetch_currency_for_country(country_code: str) -> Optional[str]:
    if not country_code:
        return None
    try:
        response = requests.get(
            RESTCOUNTRIES_URL.format(code=country_code.strip()), timeout=5
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and data:
            currencies = data[0].get("currencies")
            if currencies:
                # currencies dict keys are currency codes
                return list(currencies.keys())[0]
    except (requests.RequestException, ValueError, KeyError):
        return None
    return None


def _call_api_ninjas(endpoint: str, params: Dict[str, str]) -> Optional[Dict]:
    if not API_NINJAS_KEY:
        return None
    headers = {"X-Api-Key": API_NINJAS_KEY}
    url = f"https://api.api-ninjas.com/v1/{endpoint}"
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list) and payload:
            return payload[0]
        if isinstance(payload, dict):
            return payload
    except (requests.RequestException, ValueError):
        return None
    return None


def fetch_average_fuel_price(country_code: str, region: Optional[str] = None) -> Optional[Decimal]:
    country_code = (country_code or "").upper()
    if API_NINJAS_KEY:
        params = {"country": country_code}
        if region:
            params["state"] = region
        data = _call_api_ninjas("fuelprice", params)
        if data:
            price = data.get("gasoline") or data.get("diesel")
            if price:
                return _safe_decimal(price)
    if country_code == "US":
        try:
            response = requests.get(EIA_GAS_PRICE_URL, timeout=5)
            response.raise_for_status()
            payload = response.json()
            series_data = payload["series"][0]["data"][0][1]
            usd_per_gallon = Decimal(str(series_data))
            liters_per_gallon = Decimal("3.78541")
            return (usd_per_gallon / liters_per_gallon).quantize(Decimal("0.001"))
        except (requests.RequestException, ValueError, KeyError, IndexError):
            return None
    return None


def fetch_average_electricity_price(country_code: str) -> Optional[Decimal]:
    country_code = (country_code or "").upper()
    if API_NINJAS_KEY:
        data = _call_api_ninjas("electricity", {"country": country_code})
        if data:
            price = data.get("price_per_kwh") or data.get("residential")
            if price:
                return _safe_decimal(price)
    return None


def fetch_average_tax_rate(country_code: str, region: Optional[str] = None) -> Optional[Decimal]:
    country_code = (country_code or "").upper()
    if API_NINJAS_KEY:
        params = {"country": country_code}
        if region:
            params["state"] = region
        data = _call_api_ninjas("salestax", params)
        if data:
            tax_rate = data.get("total_rate") or data.get("rate")
            if tax_rate:
                return _safe_decimal(tax_rate) * Decimal("100")
    return None


def gather_suggested_data(country_code: str, region: Optional[str] = None) -> SuggestedData:
    currency = fetch_currency_for_country(country_code)
    fuel_price = fetch_average_fuel_price(country_code, region)
    electricity_price = fetch_average_electricity_price(country_code)
    tax_rate = fetch_average_tax_rate(country_code, region)
    return SuggestedData(
        currency_code=currency,
        fuel_price_per_liter=fuel_price,
        electricity_price_per_kwh=electricity_price,
        tax_rate_percent=tax_rate,
    )


def _calculate_finance_schedule(
    principal: Decimal, interest_rate_percent: Decimal, term_months: int
) -> Dict[str, Decimal]:
    principal = principal.quantize(Decimal("0.01"))
    if term_months <= 0 or principal <= 0:
        return {"monthly_payment": Decimal("0"), "total_paid": Decimal("0")}

    monthly_rate = (interest_rate_percent / Decimal("100")) / Decimal("12")
    if monthly_rate == 0:
        monthly_payment = principal / term_months
    else:
        factor = (Decimal(1) + monthly_rate) ** term_months
        monthly_payment = principal * (monthly_rate * factor) / (factor - Decimal(1))
    total_paid = monthly_payment * term_months
    return {
        "monthly_payment": monthly_payment.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "total_paid": total_paid.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
    }


def estimate_car_cost(data: Dict) -> Dict[str, Decimal | Dict[str, Decimal]]:
    ownership_years = Decimal(str(data["ownership_period_years"]))
    purchase_price = _safe_decimal(data.get("car_purchase_price"))
    incentives = _safe_decimal(data.get("incentives_rebates"))
    tax_rate_percent = _safe_decimal(data.get("local_tax_rate"))
    tax_rate = tax_rate_percent / Decimal("100")

    taxable_base = max(purchase_price - incentives, Decimal("0"))
    tax_amount = (taxable_base * tax_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    acquisition_breakdown: Dict[str, Decimal] = {}
    purchase_type = data.get("purchase_type")

    if purchase_type == "cash":
        acquisition_total = taxable_base + tax_amount
        acquisition_breakdown["Upfront payment"] = acquisition_total
    elif purchase_type == "finance":
        down_payment = _safe_decimal(data.get("finance_down_payment"))
        principal = max(taxable_base - down_payment, Decimal("0"))
        schedule = _calculate_finance_schedule(
            principal + tax_amount,
            _safe_decimal(data.get("finance_interest_rate")),
            int(data.get("finance_term_months")),
        )
        acquisition_total = schedule["total_paid"] + down_payment
        acquisition_breakdown.update(
            {
                "Down payment": down_payment,
                "Financed total": schedule["total_paid"],
                "Taxes": tax_amount,
            }
        )
    elif purchase_type == "lease":
        lease_term = int(data.get("lease_term_months"))
        lease_payment = _safe_decimal(data.get("lease_monthly_payment"))
        drive_off = _safe_decimal(data.get("lease_drive_off_cost"))
        lease_total = lease_payment * lease_term + drive_off
        tax_on_lease = (lease_total * tax_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        acquisition_total = lease_total + tax_on_lease
        acquisition_breakdown.update(
            {
                "Lease payments": lease_payment * lease_term,
                "Drive-off": drive_off,
                "Lease taxes": tax_on_lease,
            }
        )
    else:
        acquisition_total = taxable_base + tax_amount
        acquisition_breakdown["Upfront payment"] = acquisition_total

    annual_mileage = Decimal(str(data.get("annual_mileage", 0)))
    fuel_consumption = _safe_decimal(data.get("fuel_consumption_per_100km"))
    electricity_consumption = _safe_decimal(data.get("electricity_consumption_per_100km"))
    gas_price = _safe_decimal(data.get("gas_price_per_liter"))
    electricity_price = _safe_decimal(data.get("electricity_price_per_kwh"))

    annual_fuel_cost = Decimal("0")
    annual_electric_cost = Decimal("0")

    if fuel_consumption and gas_price:
        liters_per_year = (annual_mileage / Decimal("100")) * fuel_consumption
        annual_fuel_cost = (liters_per_year * gas_price).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    if electricity_consumption and electricity_price:
        kwh_per_year = (annual_mileage / Decimal("100")) * electricity_consumption
        annual_electric_cost = (kwh_per_year * electricity_price).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    insurance = _safe_decimal(data.get("insurance_cost_annual"))
    maintenance = _safe_decimal(data.get("maintenance_cost_annual"))
    registration = _safe_decimal(data.get("registration_fees_annual"))
    parking = _safe_decimal(data.get("parking_cost_annual"))
    other = _safe_decimal(data.get("other_recurring_costs"))

    annual_recurring_total = annual_fuel_cost + annual_electric_cost + insurance + maintenance + registration + parking + other
    recurring_total = (annual_recurring_total * ownership_years).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    charging_installation = _safe_decimal(data.get("charging_installation_cost"))
    residual_value = _safe_decimal(data.get("residual_value"))

    total_cost = acquisition_total + recurring_total + charging_installation - residual_value
    total_cost = total_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    monthly_cost = (total_cost / (ownership_years * Decimal("12"))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    ) if ownership_years else Decimal("0.00")

    breakdown = {
        "Acquisition": acquisition_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "Energy": (annual_fuel_cost + annual_electric_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "Insurance": (insurance * ownership_years).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "Maintenance": (maintenance * ownership_years).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "Registration": (registration * ownership_years).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "Parking": (parking * ownership_years).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "Other recurring": (other * ownership_years).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "Charging infrastructure": charging_installation.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        "Residual credit": residual_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
    }

    return {
        "total_cost": total_cost,
        "monthly_cost": monthly_cost,
        "annual_recurring_total": annual_recurring_total.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        "breakdown": breakdown,
        "annual_fuel_cost": annual_fuel_cost,
        "annual_electric_cost": annual_electric_cost,
        "acquisition_breakdown": acquisition_breakdown,
    }
