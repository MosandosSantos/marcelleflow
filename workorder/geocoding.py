import json
import urllib.parse
import urllib.request

from django.conf import settings


def geocode_address(address):
    provider = getattr(settings, 'GEOCODER_PROVIDER', 'nominatim').lower()

    if not address:
        return None, None

    if provider == 'google':
        api_key = getattr(settings, 'GOOGLE_GEOCODE_API_KEY', None)
        if not api_key:
            return None, None
        params = urllib.parse.urlencode({'address': address, 'key': api_key})
        url = f'https://maps.googleapis.com/maps/api/geocode/json?{params}'
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        if data.get('status') != 'OK':
            return None, None
        location = data['results'][0]['geometry']['location']
        return float(location['lat']), float(location['lng'])

    # Default: Nominatim (OpenStreetMap)
    params = urllib.parse.urlencode({'q': address, 'format': 'json', 'limit': 1})
    url = f'https://nominatim.openstreetmap.org/search?{params}'
    headers = {
        'User-Agent': getattr(settings, 'GEOCODER_USER_AGENT', 'EsferaWork'),
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as response:
        data = json.loads(response.read().decode('utf-8'))
    if not data:
        return None, None
    return float(data[0]['lat']), float(data[0]['lon'])
