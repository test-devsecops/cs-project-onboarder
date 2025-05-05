import os
import sys

class Config:
    
    def __init__(self):
        """Initialize and load configuration from environment variables."""
        self.token = os.getenv('CX_TOKEN')
        self.tenant_name = os.getenv('TENANT_NAME')
        self.tenant_iam_url = os.getenv('TENANT_IAM_URL')
        self.tenant_url = os.getenv('TENANT_URL')

        missing = [var for var in ['CX_TOKEN', 'TENANT_NAME', 'TENANT_IAM_URL', 'TENANT_URL'] if os.getenv(var) is None]
        if missing:
            print(f"Error: Missing required environment variables: {', '.join(missing)}")
            sys.exit(1)

    def get_config(self):
        """Return the loaded configuration values."""
        return self.token, self.tenant_name, self.tenant_iam_url, self.tenant_url
