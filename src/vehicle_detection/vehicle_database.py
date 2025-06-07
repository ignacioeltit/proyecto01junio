# Base de datos de vehículos para detección automática

VEHICLE_DATABASE = {
    "toyota_hilux_2018_diesel": {
        "identification": {
            "vin_pattern": "MR0FB8CD3H0320802",
            "make": "Toyota",
            "model": "Hilux DX 4X4 2.4",
            "year": 2018,
            "engine": "2GD-FTV 2.4L Diesel Turbo"
        },
        "optimal_pids": ["rpm", "vel", "temp", "carga_motor", "boost_pressure", "fuel_rate"],
        "diesel_specific_pids": ["fuel_rail_pressure_abs", "turbo_rpm", "dpf_temperature", "egr_commanded"],
        "settings": {
            "temp_warning": 95,
            "rpm_redline": 3400,
            "boost_max": 250
        }
    }
}
