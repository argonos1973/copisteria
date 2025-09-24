import urllib.request
import json

# Base URL of the Flask app
BASE_URL = 'http://localhost:5001'

# List of endpoints to test
ENDPOINTS = [
    {'path': '/api/productos', 'method': 'GET', 'expected_status': 200},
    {'path': '/api/contactos/paginado', 'method': 'GET', 'expected_status': 200},
    {'path': '/api/tickets/paginado', 'method': 'GET', 'expected_status': 200},
    {'path': '/api/facturas/paginado', 'method': 'GET', 'expected_status': 200},
    {'path': '/api/proformas/siguiente_numero', 'method': 'GET', 'expected_status': 200},
]

def test_endpoints():
    results = []
    for endpoint in ENDPOINTS:
        url = BASE_URL + endpoint['path']
        req = urllib.request.Request(url, method=endpoint['method'])
        try:
            with urllib.request.urlopen(req) as response:
                status = response.status
                if status == endpoint['expected_status']:
                    results.append({'endpoint': endpoint['path'], 'status': 'SUCCESS', 'status_code': status})
                else:
                    results.append({'endpoint': endpoint['path'], 'status': 'FAILED', 'status_code': status, 'expected': endpoint['expected_status']})
        except urllib.error.HTTPError as e:
            results.append({'endpoint': endpoint['path'], 'status': 'ERROR', 'status_code': e.code, 'error': str(e)})
        except Exception as e:
            results.append({'endpoint': endpoint['path'], 'status': 'EXCEPTION', 'error': str(e)})
    return results

if __name__ == '__main__':
    test_results = test_endpoints()
    print("Test Results:")
    for result in test_results:
        print(f"Endpoint: {result['endpoint']}")
        if result['status'] == 'SUCCESS':
            print("  Status: SUCCESS")
            print(f"  Status Code: {result['status_code']}")
        elif result['status'] == 'FAILED':
            print("  Status: FAILED")
            print(f"  Expected Status: {result['expected']}, Actual Status: {result['status_code']}")
        else:
            print(f"  Status: {result['status']}")
            if 'status_code' in result:
                print(f"  Status Code: {result['status_code']}")
            print(f"  Error: {result['error']}")
        print()
