# Temporary Email API

A Python Flask API and web interface for generating and managing temporary email addresses to receive emails.

## Features

- **Generate Temporary Emails**: Create disposable email addresses on demand
- **Email Management**: View, read, and delete received emails
- **Privacy Protection**: Keep your primary email safe from spam and unwanted services
- **RESTful API**: Full API access for integration with other applications
- **Web Interface**: User-friendly interface for managing temporary emails
- **GoatBot Integration**: Command for using temp emails with GoatBot

## API Documentation

The API provides the following endpoints:

- `POST /api/generate` - Generate a new temporary email address
- `GET /api/emails/{email_address}` - Get all emails for a specific address
- `GET /api/emails/{email_address}/{message_id}` - Get content of a specific email
- `DELETE /api/emails/{email_address}/{message_id}` - Delete a specific email
- `DELETE /api/delete/{email_address}` - Delete a temporary email account

Complete API documentation is available in the web interface at `/documentation`.

## Rate Limits

To prevent abuse, the API implements rate limiting:

- Generate Email: 5 requests per minute
- Get Emails: 60 requests per minute
- Get Email Content: 60 requests per minute
- Delete Email: 30 requests per minute
- Delete Account: 5 requests per minute

## GoatBot Integration

This project includes a GoatBot command (`goatbot_tempmail.js`) that allows users to interact with the temporary email API through GoatBot. The command supports:

- Generating temporary emails
- Checking for received emails
- Viewing email content
- Deleting emails or accounts

### Command Usage:

```
!tempmail generate - Create a new temporary email
!tempmail check - Check for new emails
!tempmail view [MESSAGE_ID] - View a specific email
!tempmail delete [MESSAGE_ID] - Delete an email
!tempmail delete all - Delete your temporary email account
```

## Setup

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   python main.py
   ```

The application will be available at `http://localhost:5000`.

## Tech Stack

- **Backend**: Python, Flask
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **API Service**: Mail.tm API
- **Rate Limiting**: Custom in-memory implementation

## License

This project is open-source and available under the MIT License.# tempmail
