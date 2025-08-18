from functools import wraps

import requests
import time

class ExceptionHandler:
    @staticmethod
    def handle_exception(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.HTTPError as err:
                print("HTTP Error:", err)
                return None
            except requests.exceptions.RequestException as e:
                print(f"RequestException error occurred: {e}")
                return None
            except Exception as err:
                print("An unexpected error occurred:", err)
                return None
        return wrapper
    
    @staticmethod
    def handle_exception_with_retries(logger=None, retries=3, delay=2):
        def decorator(func):
            def wrapper(*args, **kwargs):
                attempt = 0
                while attempt < retries:
                    try:
                        return func(*args, **kwargs)
                    except requests.exceptions.HTTPError as err:
                        msg = f"HTTP Error: {err}"
                    except requests.exceptions.RequestException as err:
                        msg = f"RequestException error occurred: {err}"
                    except Exception as err:
                        msg = f"An unexpected error occurred: {err}"
                    else:
                        break

                    attempt += 1
                    if logger:
                        logger.error(f"{msg} | Retry {attempt}/{retries}")
                        print(f"{msg} | Retry {attempt}/{retries}")
                    else:
                        print(f"{msg} | Retry {attempt}/{retries}")

                    if attempt < retries:
                        time.sleep(delay)
                return None
            return wrapper
        return decorator
    
    @staticmethod
    def handle_exception_with_retries_and_refresh(logger=None, retries=3, delay=2, get_new_token_func=None):
        """
        Decorator to handle exceptions with retries and optional token refresh on 401.

        get_new_token_func: a callable to get a new access token, e.g.
            lambda self, refresh_token, base_url, endpoint: self.get_access_token(refresh_token, base_url, endpoint)
        """
        def decorator(func):
            @wraps(func)
            def wrapper(self, access_token, *args, **kwargs):
                attempt = 0
                while attempt < retries:
                    try:
                        return func(self, access_token, *args, **kwargs)

                    except requests.exceptions.HTTPError as err:
                        msg = f"HTTP Error: {err}"
                        # Refresh token on 401 if function is provided
                        if err.response is not None and err.response.status_code == 401 and get_new_token_func:
                            print("Access token expired. Refreshing...")
                            access_token = get_new_token_func(self, kwargs.get("refresh_token"), kwargs.get("base_url"), kwargs.get("token_endpoint"))
                            continue  # retry immediately after refreshing

                    except requests.exceptions.RequestException as err:
                        msg = f"RequestException error occurred: {err}"
                    except Exception as err:
                        msg = f"An unexpected error occurred: {err}"

                    attempt += 1
                    if logger:
                        logger.error(f"{msg} | Retry {attempt}/{retries}")
                        print(f"{msg} | Retry {attempt}/{retries}")
                    else:
                        print(f"{msg} | Retry {attempt}/{retries}")

                    if attempt < retries:
                        time.sleep(delay)

                return None  # if all retries fail
            return wrapper
        return decorator