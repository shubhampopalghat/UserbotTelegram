# Telegram UserBot

A powerful Telegram userbot with advanced group management features and automated commands.

## Features

### 🔐 Authentication
- **Secure Login**: Phone number, OTP, and 2FA support
- **Retry Logic**: 3 attempts for each authentication step
- **Session Management**: Persistent login sessions

### 🎮 Interactive Menu
1. **Login** - Authenticate with your Telegram account
2. **Activate** - Start the userbot and listen for commands
3. **Exit** - Safely disconnect and exit

### 🤖 Available Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `/Aban` | Ban all group members | Type `/Aban` in any group |
| `#NexoUnion` | Delete service messages | Type `#NexoUnion` in any group |
| `.a` | Show active status | Type `.a` anywhere |
| `.join` | Join multiple groups | `.join https://t.me/group1 https://t.me/group2` |
| `.left` | Leave multiple groups | `.left https://t.me/group1 https://t.me/group2` |

### 🛡️ Service Message Cleanup
The `#NexoUnion` command removes:
- Member added/removed messages
- User joined/left messages
- Messages from deleted accounts
- Group migration messages
- **Preserves**: Group creation messages

## Installation

1. **Clone or download** this repository
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Get Telegram API credentials**:
   - Visit [my.telegram.org/apps](https://my.telegram.org/apps)
   - Create a new application
   - Note down your `api_id` and `api_hash`

## Usage

1. **Run the bot**:
   ```bash
   python main.py
   ```

2. **First-time setup**:
   - Select option `1` (Login)
   - Enter your API ID and API Hash
   - Enter your phone number with country code
   - Enter the OTP sent to your phone
   - If 2FA is enabled, enter your password

3. **Activate the bot**:
   - Select option `2` (Activate)
   - The bot will start listening for commands
   - Use the commands in any Telegram chat

## Configuration

The bot automatically creates and manages these files:
- `bot_config.json` - Stores API credentials
- `userbot_session.session` - Telegram session data

## Safety Features

- **Rate Limiting**: Built-in delays to prevent API flooding
- **Error Handling**: Comprehensive error catching and reporting
- **Self-Protection**: Won't ban the bot owner
- **Retry Logic**: Multiple attempts for failed operations

## Important Notes

⚠️ **Legal Disclaimer**: This userbot is for educational purposes. Ensure you comply with:
- Telegram's Terms of Service
- Local laws and regulations
- Group rules and admin permissions

⚠️ **Security**: 
- Keep your API credentials secure
- Don't share your session files
- Use responsibly in groups

## Troubleshooting

### Common Issues:
1. **"Invalid API credentials"**: Double-check your API ID and Hash
2. **"Phone code invalid"**: Ensure you're entering the correct OTP
3. **"Permission denied"**: Make sure you have admin rights for group operations
4. **"Rate limit exceeded"**: Wait a few minutes before retrying

### Getting Help:
- Check the console output for detailed error messages
- Ensure you have the latest version of Telethon
- Verify your internet connection

## Requirements

- Python 3.7+
- Telethon library
- Active Telegram account
- API credentials from Telegram

## License

This project is for educational purposes only. Use responsibly and at your own risk.
