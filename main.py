import asyncio
import json
import os
import sys
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PasswordHashInvalidError
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.messages import DeleteHistoryRequest
from telethon.tl.functions.account import UpdateProfileRequest, UpdateUsernameRequest
from telethon.tl.functions.photos import DeletePhotosRequest, UploadProfilePhotoRequest
from telethon.tl.types import MessageActionChatAddUser, MessageActionChatDeleteUser, MessageActionChatJoinedByLink, MessageActionChatMigrateTo, MessageActionChannelMigrateFrom
import re

class TelegramUserBot:
    def __init__(self):
        self.config_file = 'bot_config.json'
        self.client = None
        self.config = self.load_config()
        self.is_active = False
        self.accounts = {}  # Store multiple account clients
        self.current_account = None  # Currently active account
        self.logged_accounts = []  # List of logged in accounts
        
    def load_config(self):
        """Load configuration from JSON file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        return json.loads(content)
                    else:
                        return {}
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def save_config(self, config):
        """Save configuration to JSON file"""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)
        self.config = config
    
    def display_menu(self):
        """Display the main menu"""
        print("\n" + "="*50)
        print("         TELEGRAM USERBOT MENU")
        print("="*50)
        if self.logged_accounts:
            print(f"📱 Logged Accounts: {len(self.logged_accounts)}")
            if self.current_account:
                print(f"🎯 Active: {self.current_account}")
        else:
            print("🔴 NO ACCOUNTS LOGGED IN")
        print("="*50)
        print("1) Add Account")
        print("2) Select Account")
        print("3) Activate Bot")
        print("4) Account Status")
        print("5) Exit")
        print("="*50)
    
    async def check_existing_sessions(self):
        """Check for existing sessions of all accounts"""
        if 'accounts' not in self.config:
            self.config['accounts'] = {}
            self.save_config(self.config)
        
        print("🔍 Checking for existing account sessions...")
        
        for account_name, account_data in self.config['accounts'].items():
            try:
                session_file = f"sessions/{account_name}_session"
                client = TelegramClient(session_file, account_data['api_id'], account_data['api_hash'])
                await client.connect()
                
                if await client.is_user_authorized():
                    me = await client.get_me()
                    phone = me.phone if hasattr(me, 'phone') else 'Unknown'
                    self.accounts[account_name] = {
                        'client': client,
                        'phone': phone,
                        'name': me.first_name or 'Unknown'
                    }
                    self.logged_accounts.append(account_name)
                    print(f"✅ {account_name} ({phone}) - Session valid")
                else:
                    await client.disconnect()
                    print(f"❌ {account_name} - Session expired")
            except Exception as e:
                print(f"❌ {account_name} - Session check failed: {str(e)}")
        
        if self.logged_accounts:
            self.current_account = self.logged_accounts[0]
            self.client = self.accounts[self.current_account]['client']

    async def add_account(self):
        """Add a new account"""
        print("\n--- ADD NEW ACCOUNT ---")
        
        # Get account name
        account_name = input("Enter account name (e.g., Account1, Main, etc.): ").strip()
        if not account_name:
            print("❌ Account name is required!")
            return False
        
        if account_name in self.config.get('accounts', {}):
            print("❌ Account name already exists!")
            return False
        
        # Get API credentials
        print("Please provide Telegram API credentials for this account")
        print("Get them from https://my.telegram.org/apps")
        
        api_id = input("Enter your API ID: ").strip()
        api_hash = input("Enter your API Hash: ").strip()
        
        if not api_id or not api_hash:
            print("❌ API ID and Hash are required!")
            return False
        
        try:
            api_id = int(api_id)
        except ValueError:
            print("❌ API ID must be a number!")
            return False
        
        # Create sessions directory
        os.makedirs("sessions", exist_ok=True)
        
        # Initialize client for new account
        session_file = f"sessions/{account_name}_session"
        client = TelegramClient(session_file, api_id, api_hash)
        
        try:
            await client.connect()
            
            if await client.is_user_authorized():
                print("✅ Already logged in!")
                me = await client.get_me()
                phone = me.phone if hasattr(me, 'phone') else 'Unknown'
                
                # Save account to config
                if 'accounts' not in self.config:
                    self.config['accounts'] = {}
                self.config['accounts'][account_name] = {
                    'api_id': api_id,
                    'api_hash': api_hash,
                    'phone': phone
                }
                self.save_config(self.config)
                
                # Add to active accounts
                self.accounts[account_name] = {
                    'client': client,
                    'phone': phone,
                    'name': me.first_name or 'Unknown'
                }
                self.logged_accounts.append(account_name)
                self.current_account = account_name
                self.client = client
                
                await self.update_profile(client)
                print(f"✅ Account {account_name} added successfully!")
                return True
            
            # Phone number input with retry
            for attempt in range(3):
                phone = input(f"\nAttempt {attempt + 1}/3 - Enter your phone number (with country code): ").strip()
                
                if not phone:
                    print("❌ Phone number is required!")
                    continue
                
                try:
                    await client.send_code_request(phone)
                    break
                except Exception as e:
                    print(f"❌ Error sending code: {str(e)}")
                    if attempt == 2:
                        print("❌ Failed to send code after 3 attempts!")
                        await client.disconnect()
                        return False
                    continue
            else:
                await client.disconnect()
                return False
            
            # OTP verification with retry
            for attempt in range(3):
                try:
                    code = input(f"\nAttempt {attempt + 1}/3 - Enter the verification code: ").strip()
                    
                    if not code:
                        print("❌ Verification code is required!")
                        continue
                    
                    await client.sign_in(phone, code)
                    print("✅ Successfully logged in!")
                    
                    # Get user info
                    me = await client.get_me()
                    user_phone = me.phone if hasattr(me, 'phone') else phone
                    
                    # Save account to config
                    if 'accounts' not in self.config:
                        self.config['accounts'] = {}
                    self.config['accounts'][account_name] = {
                        'api_id': api_id,
                        'api_hash': api_hash,
                        'phone': user_phone
                    }
                    self.save_config(self.config)
                    
                    # Add to active accounts
                    self.accounts[account_name] = {
                        'client': client,
                        'phone': user_phone,
                        'name': me.first_name or 'Unknown'
                    }
                    self.logged_accounts.append(account_name)
                    self.current_account = account_name
                    self.client = client
                    
                    await self.update_profile(client)
                    print(f"✅ Account {account_name} added successfully!")
                    return True
                    
                except SessionPasswordNeededError:
                    # 2FA required
                    for fa_attempt in range(3):
                        try:
                            password = input(f"\n2FA Attempt {fa_attempt + 1}/3 - Enter your 2FA password: ").strip()
                            
                            if not password:
                                print("❌ 2FA password is required!")
                                continue
                            
                            await client.sign_in(password=password)
                            print("✅ Successfully logged in with 2FA!")
                            
                            # Get user info
                            me = await client.get_me()
                            user_phone = me.phone if hasattr(me, 'phone') else phone
                            
                            # Save account to config
                            if 'accounts' not in self.config:
                                self.config['accounts'] = {}
                            self.config['accounts'][account_name] = {
                                'api_id': api_id,
                                'api_hash': api_hash,
                                'phone': user_phone
                            }
                            self.save_config(self.config)
                            
                            # Add to active accounts
                            self.accounts[account_name] = {
                                'client': client,
                                'phone': user_phone,
                                'name': me.first_name or 'Unknown'
                            }
                            self.logged_accounts.append(account_name)
                            self.current_account = account_name
                            self.client = client
                            
                            await self.update_profile(client)
                            print(f"✅ Account {account_name} added successfully!")
                            return True
                            
                        except PasswordHashInvalidError:
                            print("❌ Invalid 2FA password!")
                            if fa_attempt == 2:
                                print("❌ Failed 2FA verification after 3 attempts!")
                                await client.disconnect()
                                return False
                        except Exception as e:
                            print(f"❌ 2FA Error: {str(e)}")
                            if fa_attempt == 2:
                                await client.disconnect()
                                return False
                    await client.disconnect()
                    return False
                    
                except PhoneCodeInvalidError:
                    print("❌ Invalid verification code!")
                    if attempt == 2:
                        print("❌ Failed OTP verification after 3 attempts!")
                        await client.disconnect()
                        return False
                except Exception as e:
                    print(f"❌ Login error: {str(e)}")
                    if attempt == 2:
                        await client.disconnect()
                        return False
            
            await client.disconnect()
            return False
            
        except Exception as e:
            print(f"❌ Connection error: {str(e)}")
            if client:
                await client.disconnect()
            return False
    
    async def update_profile(self, client=None):
        """Update profile settings after login"""
        if client is None:
            client = self.client
            
        try:
            print("🔄 Updating profile settings...")
            
            # Update name to "UserBot @NexoUnion"
            await client(UpdateProfileRequest(
                first_name="UserBot @NexoUnion",
                last_name="",
                about=""
            ))
            print("✅ Profile name updated")
            
            # Remove username
            try:
                await client(UpdateUsernameRequest(username=""))
                print("✅ Username removed")
            except Exception as e:
                print(f"⚠️ Could not remove username: {str(e)}")
            
            # Delete all existing profile photos
            try:
                photos = await client.get_profile_photos('me')
                if photos:
                    photo_ids = [photo.id for photo in photos]
                    await client(DeletePhotosRequest(id=photo_ids))
                    print(f"✅ Removed {len(photo_ids)} profile photos")
            except Exception as e:
                print(f"⚠️ Could not remove profile photos: {str(e)}")
            
            # Set new profile picture
            picture_path = "pictures/ub1.png"
            if os.path.exists(picture_path):
                try:
                    with open(picture_path, 'rb') as f:
                        await client(UploadProfilePhotoRequest(
                            file=await client.upload_file(f)
                        ))
                    print("✅ New profile picture set")
                except Exception as e:
                    print(f"⚠️ Could not set profile picture: {str(e)}")
            else:
                print(f"⚠️ Profile picture not found at {picture_path}")
                # Create pictures directory if it doesn't exist
                os.makedirs("pictures", exist_ok=True)
                print("📁 Created pictures directory - please add ub1.png file")
            
            print("✅ Profile update completed")
            
        except Exception as e:
            print(f"❌ Profile update error: {str(e)}")
    
    async def select_account(self):
        """Select which account to use"""
        if not self.logged_accounts:
            print("❌ No accounts logged in! Please add an account first.")
            return
        
        print("\n--- SELECT ACCOUNT ---")
        for i, account_name in enumerate(self.logged_accounts, 1):
            account_info = self.accounts[account_name]
            status = "🎯 ACTIVE" if account_name == self.current_account else "⚪ INACTIVE"
            print(f"{i}) {account_name} ({account_info['phone']}) - {account_info['name']} {status}")
        
        try:
            choice = int(input(f"\nSelect account (1-{len(self.logged_accounts)}): "))
            if 1 <= choice <= len(self.logged_accounts):
                selected_account = self.logged_accounts[choice - 1]
                self.current_account = selected_account
                self.client = self.accounts[selected_account]['client']
                print(f"✅ Switched to {selected_account}")
            else:
                print("❌ Invalid choice!")
        except ValueError:
            print("❌ Please enter a valid number!")
    
    async def show_account_status(self):
        """Show status of all accounts"""
        print("\n--- ACCOUNT STATUS ---")
        if not self.logged_accounts:
            print("🔴 No accounts logged in")
            return
        
        for account_name in self.logged_accounts:
            account_info = self.accounts[account_name]
            status = "🎯 ACTIVE" if account_name == self.current_account else "⚪ INACTIVE"
            print(f"📱 {account_name}: {account_info['phone']} - {account_info['name']} {status}")
    
    async def activate_bot(self):
        """Activate the userbot and start listening for commands"""
        if not self.logged_accounts or not self.current_account:
            print("❌ No account selected! Please add and select an account first.")
            return
        
        if not self.client or not await self.client.is_user_authorized():
            print("❌ Current account not authorized! Please select a valid account.")
            return
        
        print("✅ Userbot activated! Listening for commands...")
        print("\nAvailable commands:")
        print("- /Aban : Ban all group members")
        print("- #NexoUnion : Delete service messages")
        print("- .a : Show active status")
        print("- .join [links] : Join groups")
        print("- .left [links] : Leave groups")
        print("\nPress Ctrl+C to stop the bot")
        
        self.is_active = True
        
        # Register event handlers
        @self.client.on(events.NewMessage(pattern=r'^/Aban$'))
        async def ban_all_members(event):
            await self.handle_ban_all(event)
        
        @self.client.on(events.NewMessage(pattern=r'^#NexoUnion$'))
        async def delete_service_messages(event):
            await self.handle_delete_service_messages(event)
        
        @self.client.on(events.NewMessage(pattern=r'^\.a$'))
        async def active_status(event):
            await self.handle_active_status(event)
        
        @self.client.on(events.NewMessage(pattern=r'^\.join'))
        async def join_groups(event):
            await self.handle_join_groups(event)
        
        @self.client.on(events.NewMessage(pattern=r'^\.left'))
        async def leave_groups(event):
            await self.handle_leave_groups(event)
        
        try:
            await self.client.run_until_disconnected()
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user")
            self.is_active = False
    
    async def handle_ban_all(self, event):
        """Handle /Aban command - ban all group members"""
        try:
            chat = await event.get_chat()
            
            if not chat.megagroup and not hasattr(chat, 'participants_count'):
                await event.reply("❌ This command only works in groups!")
                return
            
            me = await self.client.get_me()
            participants = await self.client.get_participants(chat)
            
            banned_count = 0
            failed_count = 0
            
            await event.reply(f"🚫 Starting to ban {len(participants)} members...")
            
            for participant in participants:
                if participant.id == me.id:  # Don't ban ourselves
                    continue
                
                try:
                    await self.client.kick_participant(chat, participant)
                    banned_count += 1
                    await asyncio.sleep(1)  # Rate limiting
                except Exception as e:
                    failed_count += 1
                    print(f"Failed to ban {participant.id}: {str(e)}")
            
            await event.reply(f"✅ Banned: {banned_count} | ❌ Failed: {failed_count}")
            
        except Exception as e:
            await event.reply(f"❌ Error: {str(e)}")
    
    async def handle_delete_service_messages(self, event):
        """Handle #NexoUnion command - delete service messages"""
        try:
            chat = await event.get_chat()
            deleted_count = 0
            
            status_msg = await event.reply("🗑️ Starting to delete service messages...")
            
            async for message in self.client.iter_messages(chat, limit=10000):
                # Delete all service messages by checking if message has action attribute
                if hasattr(message, 'action') and message.action:
                    try:
                        await message.delete()
                        deleted_count += 1
                        await asyncio.sleep(0.3)  # Rate limiting
                    except Exception as e:
                        print(f"Failed to delete service message {message.id}: {str(e)}")
                
                # Also delete messages from deleted accounts (no sender)
                elif message.from_id is None and hasattr(message, 'message') and message.message:
                    try:
                        await message.delete()
                        deleted_count += 1
                        await asyncio.sleep(0.3)
                    except Exception as e:
                        print(f"Failed to delete deleted account message {message.id}: {str(e)}")
            
            # Delete the initial status message
            try:
                await status_msg.delete()
            except:
                pass
            
            # Send completion message and delete it after 2 seconds
            completion_msg = await event.reply(f"✅ Deleted {deleted_count} service messages!")
            await asyncio.sleep(2)
            try:
                await completion_msg.delete()
            except:
                pass
            
        except Exception as e:
            await event.reply(f"❌ Error: {str(e)}")
    
    async def handle_active_status(self, event):
        """Handle .a command - show active status"""
        try:
            me = await self.client.get_me()
            status = "🟢 ACTIVE" if self.is_active else "🔴 INACTIVE"
            
            status_msg = await event.reply(f"**Userbot Status:** {status}\n"
                            f"**User:** {me.first_name} {me.last_name or ''}\n"
                            f"**Username:** @{me.username or 'None'}\n"
                            f"**User ID:** {me.id}")
            
            # Delete the status message after 2 seconds
            await asyncio.sleep(2)
            try:
                await status_msg.delete()
            except:
                pass
            
        except Exception as e:
            await event.reply(f"❌ Error: {str(e)}")
    
    async def handle_join_groups(self, event):
        """Handle .join command - join multiple groups"""
        try:
            message_text = event.message.message
            # Extract group links from the message - improved regex to catch all t.me links
            links = re.findall(r'(https?://t\.me/[^\s]+)', message_text)
            
            if not links:
                await event.reply("❌ No valid group links found!\nUsage: .join https://t.me/group1 https://t.me/+invitelink")
                return
            
            joined_count = 0
            failed_count = 0
            
            status_msg = await event.reply(f"🔗 Attempting to join {len(links)} groups...")
            
            for link in links:
                try:
                    print(f"Attempting to join: {link}")
                    
                    # Handle different types of Telegram links
                    if '/joinchat/' in link:
                        # Old style invite links: https://t.me/joinchat/xxxxx
                        print(f"Processing old style invite link: {link}")
                        try:
                            # Use the full link for join_chat
                            result = await self.client.join_chat(link)
                            print(f"Join result: {result}")
                        except Exception as e:
                            print(f"Failed with join_chat, trying alternative method: {str(e)}")
                            # Try importing the chat
                            from telethon.tl.functions.messages import ImportChatInviteRequest
                            hash_part = link.split('/joinchat/')[-1]
                            result = await self.client(ImportChatInviteRequest(hash_part))
                            print(f"Import result: {result}")
                    elif '/+' in link:
                        # New style private invite links: https://t.me/+xxxxx
                        print(f"Processing new style invite link: {link}")
                        try:
                            # Use the full link for join_chat
                            result = await self.client.join_chat(link)
                            print(f"Join result: {result}")
                        except Exception as e:
                            print(f"Failed with join_chat, trying alternative method: {str(e)}")
                            # Try importing the chat with the hash
                            from telethon.tl.functions.messages import ImportChatInviteRequest
                            hash_part = link.split('/+')[-1]
                            result = await self.client(ImportChatInviteRequest(hash_part))
                            print(f"Import result: {result}")
                    else:
                        # Public username links: https://t.me/username
                        username = link.split('/')[-1]
                        # Remove any query parameters
                        username = username.split('?')[0]
                        print(f"Processing public username: {username}")
                        
                        try:
                            # Try to get the entity first
                            entity = await self.client.get_entity(username)
                            result = await self.client(JoinChannelRequest(entity))
                            print(f"Join result: {result}")
                        except Exception as e:
                            print(f"Failed to get entity for {username}: {str(e)}")
                            # Try with @ prefix
                            try:
                                entity = await self.client.get_entity(f"@{username}")
                                result = await self.client(JoinChannelRequest(entity))
                                print(f"Join result with @ prefix: {result}")
                            except:
                                raise e
                    
                    joined_count += 1
                    print(f"Successfully joined: {link}")
                    await asyncio.sleep(2)  # Rate limiting
                    
                except Exception as e:
                    error_msg = str(e)
                    print(f"Failed to join {link}: {error_msg}")
                    
                    # Handle specific error cases
                    if "USER_ALREADY_PARTICIPANT" in error_msg:
                        print(f"Already in group: {link}")
                        joined_count += 1  # Count as success since we're already in
                    elif "INVITE_HASH_EXPIRED" in error_msg:
                        print(f"Invite link expired: {link}")
                        failed_count += 1
                    elif "CHANNELS_TOO_MUCH" in error_msg:
                        print(f"Too many channels joined: {link}")
                        failed_count += 1
                    elif "FLOOD_WAIT" in error_msg:
                        print(f"Rate limited, waiting...")
                        # Extract wait time and wait
                        wait_time = int(re.search(r'(\d+)', error_msg).group(1)) if re.search(r'(\d+)', error_msg) else 60
                        await asyncio.sleep(wait_time)
                        # Retry once after waiting
                        try:
                            if '/joinchat/' in link or '/+' in link:
                                await self.client.join_chat(link)
                            else:
                                username = link.split('/')[-1].split('?')[0]
                                entity = await self.client.get_entity(username)
                                await self.client(JoinChannelRequest(entity))
                            joined_count += 1
                        except:
                            failed_count += 1
                    else:
                        failed_count += 1
            
            # Delete the initial status message
            try:
                await status_msg.delete()
            except:
                pass
            
            # Send completion message and delete it after 2 seconds
            completion_msg = await event.reply(f"✅ Joined: {joined_count} | ❌ Failed: {failed_count}")
            await asyncio.sleep(2)
            try:
                await completion_msg.delete()
            except:
                pass
            
        except Exception as e:
            await event.reply(f"❌ Error: {str(e)}")
    
    async def handle_leave_groups(self, event):
        """Handle .left command - leave multiple groups"""
        try:
            message_text = event.message.message
            # Extract group links from the message
            links = re.findall(r'(https?://t\.me/[^\s]+)', message_text)
            
            if not links:
                await event.reply("❌ No valid group links found!\nUsage: .left https://t.me/group1 https://t.me/group2")
                return
            
            left_count = 0
            failed_count = 0
            
            status_msg = await event.reply(f"🚪 Attempting to leave {len(links)} groups...")
            
            for link in links:
                try:
                    print(f"Attempting to leave: {link}")
                    
                    # Handle different types of links
                    if '/joinchat/' in link or '/+' in link:
                        # For invite links, we need to get the chat first
                        try:
                            # Try to get chat info from the link
                            chat = await self.client.get_entity(link)
                            await self.client(LeaveChannelRequest(chat))
                            print(f"Left invite link group: {link}")
                        except Exception as e:
                            print(f"Failed to leave invite link {link}: {str(e)}")
                            # Try alternative method - get all dialogs and find matching chat
                            async for dialog in self.client.iter_dialogs():
                                if hasattr(dialog.entity, 'username') and dialog.entity.username:
                                    if f"t.me/{dialog.entity.username}" in link:
                                        await self.client(LeaveChannelRequest(dialog.entity))
                                        print(f"Left group via dialog search: {link}")
                                        break
                            else:
                                raise e
                    else:
                        # Public username links
                        username = link.split('/')[-1].split('?')[0]  # Remove query params
                        print(f"Processing username: {username}")
                        
                        try:
                            entity = await self.client.get_entity(username)
                            await self.client(LeaveChannelRequest(entity))
                            print(f"Left public group: {username}")
                        except Exception as e:
                            print(f"Failed to get entity for {username}: {str(e)}")
                            # Try with @ prefix
                            try:
                                entity = await self.client.get_entity(f"@{username}")
                                await self.client(LeaveChannelRequest(entity))
                                print(f"Left group with @ prefix: @{username}")
                            except:
                                raise e
                    
                    left_count += 1
                    await asyncio.sleep(2)  # Rate limiting
                    
                except Exception as e:
                    failed_count += 1
                    error_msg = str(e)
                    print(f"Failed to leave {link}: {error_msg}")
                    
                    # Handle specific errors
                    if "USER_NOT_PARTICIPANT" in error_msg:
                        print(f"Not in group: {link}")
                        # Don't count as failure since we're not in the group anyway
                        failed_count -= 1
            
            # Delete the initial status message
            try:
                await status_msg.delete()
            except:
                pass
            
            # Send completion message and delete it after 2 seconds
            completion_msg = await event.reply(f"✅ Left: {left_count} | ❌ Failed: {failed_count}")
            await asyncio.sleep(2)
            try:
                await completion_msg.delete()
            except:
                pass
            
        except Exception as e:
            await event.reply(f"❌ Error: {str(e)}")
    
    async def run(self):
        """Main run loop"""
        # Check for existing sessions on startup
        await self.check_existing_sessions()
        
        while True:
            try:
                self.display_menu()
                choice = input("\nEnter your choice (1-5): ").strip()
                
                if choice == '1':
                    success = await self.add_account()
                    if success:
                        print("✅ Account added successfully!")
                    else:
                        print("❌ Failed to add account!")
                
                elif choice == '2':
                    await self.select_account()
                
                elif choice == '3':
                    await self.activate_bot()
                
                elif choice == '4':
                    await self.show_account_status()
                
                elif choice == '5':
                    print("👋 Goodbye!")
                    # Disconnect all clients
                    for account_name, account_info in self.accounts.items():
                        try:
                            await account_info['client'].disconnect()
                        except:
                            pass
                    sys.exit(0)
                
                else:
                    print("❌ Invalid choice! Please select 1-5.")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                # Disconnect all clients
                for account_name, account_info in self.accounts.items():
                    try:
                        await account_info['client'].disconnect()
                    except:
                        pass
                sys.exit(0)
            except Exception as e:
                print(f"❌ Unexpected error: {str(e)}")

async def main():
    """Main function"""
    bot = TelegramUserBot()
    await bot.run()

if __name__ == "__main__":
    print("🚀 Starting Telegram UserBot...")
    asyncio.run(main())