from dataclasses import dataclass
from typing import List


@dataclass
class Tool:
    slug: str
    name: str
    description: str
    url_name: str


@dataclass
class ToolCategory:
    slug: str
    name: str
    description: str
    tools: List[Tool]


TOOL_REGISTRY: List[ToolCategory] = [
    ToolCategory(
        slug="calculators",
        name="Calculators",
        description="Analysis and estimation tools for ownership planning.",
        tools=[
            Tool(
                slug="car-cost-estimator",
                name="Car Cost Estimation",
                description="Estimate the long-term cost of owning or leasing a vehicle using regionalized assumptions.",
                url_name="car_cost_estimator",
            )
        ],
    )
]


def get_tool_categories() -> List[ToolCategory]:
    return TOOL_REGISTRY
