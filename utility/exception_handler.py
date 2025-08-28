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
    def handle_exception_with_retries(retries=1, delay=1.3):
        def decorator(func):
            def wrapper(*args, **kwargs):
                self = args[0]  # the first arg of a class method is 'self'
                logger = getattr(self, 'logger', None)

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

                    attempt += 1
                    if logger:
                        logger.error(f"{msg} | Retry {attempt}/{retries}")
                    else:
                        print(f"{msg} | Retry {attempt}/{retries}")

                    if attempt < retries:
                        time.sleep(delay)
                return None
            return wrapper
        return decorator