"""
Geocoding e locais próximos via APIs gratuitas:
  - Nominatim (OpenStreetMap) — lat/lng por endereço
  - Overpass API (OSM) — locais próximos sem API key
"""
from __future__ import annotations
import json
import logging
import time
import urllib.parse
import urllib.request
from typing import Any

log = logging.getLogger("leilao.geo")

_NOMINATIM = "https://nominatim.openstreetmap.org/search"
_OVERPASS  = "https://overpass-api.de/api/interpreter"
_UA = "SP-Leiloes-Monitor/2.0 (github.com/seu-usuario/leilao)"

def _get(url: str, params: dict | None = None) -> Any:
    full = url + ("?" + urllib.parse.urlencode(params) if params else "")
    req  = urllib.request.Request(full, headers={"User-Agent": _UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def geocodificar(endereco: str, cidade: str, estado: str = "SP") -> tuple[float, float] | None:
    """Retorna (lat, lng) ou None se não encontrar."""
    query = f"{endereco}, {cidade}, {estado}, Brasil"
    try:
        data = _get(_NOMINATIM, {"q": query, "format": "json", "limit": 1, "countrycodes": "br"})
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
        # Tentar só cidade
        data = _get(_NOMINATIM, {"q": f"{cidade}, {estado}, Brasil", "format": "json", "limit": 1, "countrycodes": "br"})
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        log.debug("Geocoding falhou para %s: %s", endereco, e)
    return None


def locais_proximos(lat: float, lng: float, raio: int = 2000) -> dict[str, Any]:
    """
    Busca locais próximos via Overpass (OpenStreetMap).
    Retorna dict com as categorias e a distância do mais próximo.
    """
    import math

    def dist_m(la1: float, lo1: float, la2: float, lo2: float) -> int:
        R = 6_371_000
        dl = math.radians(la2 - la1)
        dlo = math.radians(lo2 - lo1)
        a = math.sin(dl/2)**2 + math.cos(math.radians(la1)) * math.cos(math.radians(la2)) * math.sin(dlo/2)**2
        return int(R * 2 * math.asin(math.sqrt(a)))

    # Query Overpass: buscar metrô, trem, hospital, escola, shopping em raio
    ql = f"""
    [out:json][timeout:15];
    (
      node["railway"~"station|subway_entrance"](around:{raio},{lat},{lng});
      node["amenity"="hospital"](around:{raio},{lat},{lng});
      node["amenity"~"school|university|college"](around:{raio},{lat},{lng});
      node["shop"="mall"](around:{raio},{lat},{lng});
      way["shop"="mall"](around:{raio},{lat},{lng});
      node["amenity"="marketplace"](around:{raio},{lat},{lng});
    );
    out center;
    """
    result: dict[str, Any] = {}
    try:
        data = _get(_OVERPASS, {"data": ql})
        elements = data.get("elements", [])

        cats: dict[str, list] = {"metro": [], "hospital": [], "escola": [], "shopping": []}
        for el in elements:
            la = el.get("lat") or el.get("center", {}).get("lat")
            lo = el.get("lon") or el.get("center", {}).get("lon")
            tags = el.get("tags", {})
            if not la: continue
            d = dist_m(lat, lng, float(la), float(lo))
            name = tags.get("name", "")
            railway = tags.get("railway", "")
            amenity = tags.get("amenity", "")
            shop    = tags.get("shop", "")
            if railway in ("station", "subway_entrance"):
                cats["metro"].append({"nome": name or "Estação", "dist": d})
            elif amenity == "hospital":
                cats["hospital"].append({"nome": name or "Hospital", "dist": d})
            elif amenity in ("school", "university", "college"):
                cats["escola"].append({"nome": name or "Escola", "dist": d})
            elif shop == "mall":
                cats["shopping"].append({"nome": name or "Shopping", "dist": d})

        LABEL = {"metro": "🚇 Metrô/Trem", "hospital": "🏥 Hospital", "escola": "🏫 Escola", "shopping": "🏬 Shopping"}
        for cat, items in cats.items():
            if items:
                mais_perto = min(items, key=lambda x: x["dist"])
                result[cat] = {"label": LABEL[cat], "nome": mais_perto["nome"], "dist_m": mais_perto["dist"]}

    except Exception as e:
        log.debug("Overpass falhou: %s", e)

    return result
