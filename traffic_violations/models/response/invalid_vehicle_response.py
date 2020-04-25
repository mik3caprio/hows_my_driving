from dataclasses import dataclass, field
from typing import List

from traffic_violations.models.response.vehicle_response \
    import VehicleResponse


@dataclass
class InvalidVehicleResponse(VehicleResponse):
    """ Represents the output of an invalid vehicle lookup."""
