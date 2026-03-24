import gspread
from google.oauth2.service_account import Credentials
from config_lambda import G_SPREADSHEET_NAME, SHEET_NAME, CREDENTIALS_JSON

def get_worksheet():
    """
    Connects to Google Sheets using the baked-in service account JSON.
    """
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Load credentials from the path defined in config_lambda (TASK_ROOT/credentials.json)
    creds = Credentials.from_service_account_file(CREDENTIALS_JSON, scopes=scopes)
    client = gspread.authorize(creds)
    
    return client.open(G_SPREADSHEET_NAME).worksheet(SHEET_NAME)
