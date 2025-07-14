import requests
import sys

class HttpRequests:

    def post_api_request(self, url, headers=None, data=None, params=None, json=None):

        # Make the request
        response = requests.post(url, headers=headers, data=data, params=params, json=json, timeout=120)

        # Debug print statements
        # print("Request URL:", response.url)
        # print("Status Code:", response.status_code)
        # print("Request Headers:", response.request.headers)
        # print("Request Body:", response.request.body)

        valid_status_codes = [200, 201]

        # Check if the response status code is in the array
        if response.status_code in valid_status_codes:
            return response.json()
        else:
            response.raise_for_status()

    def get_api_request(self, url, headers=None, data=None, params=None, json=None):

        # Make the request
        response = requests.get(url, headers=headers, data=data, params=params, json=json)

        # Debug print statements
        # print("Request URL:", response.url)
        # print("Status Code:", response.status_code)
        # print("Request Headers:", response.request.headers)
        # print("Request Body:", response.request.body)

        valid_status_codes = [200, 201]

        # Check if the response status code is in the array
        if response.status_code in valid_status_codes:
            return response.json()
        else:
            response.raise_for_status()
    
    def patch_api_request(self, url, headers=None, data=None, params=None, json=None):

        # Make the request
        response = requests.patch(url, headers=headers, data=data, params=params, json=json)

        # Debug print statements
        # print("Request URL:", response.url)
        # print("Status Code:", response.status_code)
        # print("Request Headers:", response.request.headers)
        # print("Request Body:", response.request.body)

        valid_status_codes = [200, 201]

        # Check if the response status code is in the array
        if response.status_code in valid_status_codes:
            return response.json()
        else:
            response.raise_for_status()

    def delete_api_request(self, url, headers=None, data=None, params=None, json=None):

        # Make the request
        response = requests.delete(url, headers=headers, data=data, params=params, json=json, timeout=360)

        # Debug print statements
        # print("Request URL:", response.url)
        # print("Status Code:", response.status_code)
        # print("Request Headers:", response.request.headers)
        # print("Request Body:", response.request.body)

        valid_status_codes = [200, 204]  # Typically for successful deletion

        # Check if the response status code is in the array
        if response.status_code in valid_status_codes:
            # For successful deletion, typically, there's no response body
            return None
        else:
            response.raise_for_status()
    
    def put_api_request(self, url, headers=None, data=None, params=None, json=None):
        
        response = requests.put(url, headers=headers, data=data, params=params, json=json, timeout=120)

        # Debug print statements
        # print("Request URL:", response.url)
        # print("Status Code:", response.status_code)
        # print("Request Headers:", response.request.headers)
        # print("Request Body:", response.request.body)

        valid_status_codes = [200, 204]  # 204 is for successful update with no content

        # Check if the response status code is in the array
        if response.status_code in valid_status_codes:
            # For successful deletion, typically, there's no response body
            return None
        else:
            response.raise_for_status()
