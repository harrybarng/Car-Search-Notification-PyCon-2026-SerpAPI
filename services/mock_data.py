from __future__ import annotations

from typing import Any

# Realistic Google Shopping-format results for common makes/models.
# Mirrors the exact fields the filter engine reads: title, snippet,
# extracted_price, link, source.
_MOCK_LISTINGS: list[dict[str, Any]] = [
    {
        "title": "2023 Audi A4 Premium Plus 45 TFSI",
        "snippet": "12,500 miles, one owner, clean Carfax, heated seats, sunroof",
        "extracted_price": 38900.0,
        "link": "https://mock.autotrader.com/listing/audi-a4-001",
        "source": "AutoTrader [MOCK]",
    },
    {
        "title": "2024 Audi A4 Premium Plus quattro",
        "snippet": "3,200 miles, still under factory warranty, Bang & Olufsen audio",
        "extracted_price": 44500.0,
        "link": "https://mock.autotrader.com/listing/audi-a4-002",
        "source": "AutoTrader [MOCK]",
    },
    {
        "title": "2022 Audi A4 Premium 40 TFSI",
        "snippet": "28,000 miles, dealer certified pre-owned, navigation",
        "extracted_price": 31750.0,
        "link": "https://mock.cargurus.com/listing/audi-a4-003",
        "source": "CarGurus [MOCK]",
    },
    {
        "title": "2021 Audi A4 Premium Plus S line",
        "snippet": "41,000 miles, sport package, black optic, virtual cockpit",
        "extracted_price": 29900.0,
        "link": "https://mock.cars.com/listing/audi-a4-004",
        "source": "Cars.com [MOCK]",
    },
    {
        "title": "2023 BMW 3 Series 330i xDrive",
        "snippet": "9,800 miles, M Sport package, driver assistance pkg, heads-up display",
        "extracted_price": 42000.0,
        "link": "https://mock.autotrader.com/listing/bmw-330i-001",
        "source": "AutoTrader [MOCK]",
    },
    {
        "title": "2022 BMW 3 Series 330i Sedan",
        "snippet": "22,400 miles, premium pkg, wireless charging, parking sensors",
        "extracted_price": 36500.0,
        "link": "https://mock.cargurus.com/listing/bmw-330i-002",
        "source": "CarGurus [MOCK]",
    },
    {
        "title": "2024 BMW 3 Series 330e Plug-In Hybrid",
        "snippet": "6,100 miles, sport line, heated steering wheel, LED headlights",
        "extracted_price": 47200.0,
        "link": "https://mock.cars.com/listing/bmw-330e-001",
        "source": "Cars.com [MOCK]",
    },
    {
        "title": "2023 Mercedes-Benz C-Class C300 4MATIC",
        "snippet": "14,200 miles, AMG line, panoramic roof, Burmester sound system",
        "extracted_price": 46800.0,
        "link": "https://mock.autotrader.com/listing/mb-c300-001",
        "source": "AutoTrader [MOCK]",
    },
    {
        "title": "2022 Mercedes-Benz C-Class C300 Sedan",
        "snippet": "31,000 miles, sport trim, backup camera, Apple CarPlay",
        "extracted_price": 38200.0,
        "link": "https://mock.cargurus.com/listing/mb-c300-002",
        "source": "CarGurus [MOCK]",
    },
    {
        "title": "2021 Tesla Model 3 Long Range AWD",
        "snippet": "27,500 miles, autopilot, glass roof, premium interior, 358mi range",
        "extracted_price": 34900.0,
        "link": "https://mock.autotrader.com/listing/tesla-m3-001",
        "source": "AutoTrader [MOCK]",
    },
    {
        "title": "2023 Tesla Model 3 RWD",
        "snippet": "8,000 miles, standard range, basic autopilot, white interior",
        "extracted_price": 31500.0,
        "link": "https://mock.cargurus.com/listing/tesla-m3-002",
        "source": "CarGurus [MOCK]",
    },
    {
        "title": "2022 Toyota Camry XSE V6",
        "snippet": "19,400 miles, sport trim, wireless CarPlay, JBL audio, sunroof",
        "extracted_price": 28900.0,
        "link": "https://mock.cars.com/listing/camry-xse-001",
        "source": "Cars.com [MOCK]",
    },
    {
        "title": "2023 Toyota Camry TRD",
        "snippet": "11,200 miles, sport suspension, 18in black wheels, red interior stitching",
        "extracted_price": 32400.0,
        "link": "https://mock.autotrader.com/listing/camry-trd-001",
        "source": "AutoTrader [MOCK]",
    },
    {
        "title": "2021 Honda Accord Sport 2.0T",
        "snippet": "33,600 miles, one owner, Honda Sensing, remote start, heated seats",
        "extracted_price": 24500.0,
        "link": "https://mock.cargurus.com/listing/accord-sport-001",
        "source": "CarGurus [MOCK]",
    },
    {
        "title": "2022 Honda Accord EX-L",
        "snippet": "21,000 miles, leather, sunroof, wireless charging, lane keep assist",
        "extracted_price": 27800.0,
        "link": "https://mock.cars.com/listing/accord-exl-001",
        "source": "Cars.com [MOCK]",
    },
]


def get_mock_results(make: str, model: str) -> list[dict[str, Any]]:
    """Return mock Shopping results matching the make/model (case-insensitive)."""
    key = f"{make} {model}".lower()
    return [
        r for r in _MOCK_LISTINGS
        if make.lower() in r["title"].lower() and model.lower() in r["title"].lower()
    ] or [
        # Fallback: return two generic entries so the pipeline always has something to filter
        {
            "title": f"2023 {make} {model} Base Trim",
            "snippet": "15,000 miles, clean title, one owner",
            "extracted_price": 29999.0,
            "link": f"https://mock.autotrader.com/listing/{make.lower()}-{model.lower()}-fallback-1",
            "source": "AutoTrader [MOCK]",
        },
        {
            "title": f"2022 {make} {model} Premium",
            "snippet": "28,000 miles, dealer certified, navigation",
            "extracted_price": 24500.0,
            "link": f"https://mock.autotrader.com/listing/{make.lower()}-{model.lower()}-fallback-2",
            "source": "CarGurus [MOCK]",
        },
    ]
