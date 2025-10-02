from django.urls import path

from .views import CarCostEstimatorView

urlpatterns = [
    path("car-cost-estimator/", CarCostEstimatorView.as_view(), name="car_cost_estimator"),
]
