import json
import asyncio
import logging
import redis.asyncio as aioredis
from typing import Callable, Any, Dict

from even_glasses.models import Command, SubCommand

async def handle_heartbeat(side: str, sender: str, data: bytes) -> asyncio.Future:
    """
    Handle the HEARTBEAT command from the device.

    Command: HEARTBEAT (0x25)
    """
    logging.info(f"Heartbeat received from {side}")
    # Additional processing can be implemented here

async def handle_start_ai(side: str, sender: str, data: bytes) -> asyncio.Future:
    """
    Handle the START_AI command including subcommands.

    Command: START_AI (0xF5)
    Subcommands:
      - 0x00: Exit to dashboard manually. double tap on the touchpad
      - 0x01: Page up/down control in manual mode
      - 0x17: Start Even AI
      - 0x18: Stop Even AI recording
    """
    if len(data) < 2:
        logging.warning(f"Invalid data length for START_AI command from {side}")
        return

    sub_command_byte = data[1]
    try:
        sub_command = SubCommand(sub_command_byte)
    except ValueError:
        logging.warning(
            f"Unknown subcommand: 0x{sub_command_byte:02X} received from {side}"
        )
        return

    logging.info(
        f"START_AI command with subcommand {sub_command.name} received from {side}"
    )

    # Handle subcommands
    if sub_command == SubCommand.EXIT:
        # Handle exit to dashboard
        logging.info(f"Handling EXIT to dashboard command from {side}")
        
async def handle_open_mic(side: str, sender: str, data: bytes) -> asyncio.Future:
    """
    Handle the OPEN_MIC command from the device.

    Command: OPEN_MIC (0x11)
    """
    logging.info(f"Open mic command received from {side}")
    # Additional processing can be implemented here
    
async def handle_mic_response(side: str, sender: str, data: bytes) -> asyncio.Future:
    """
    Handle the MIC_RESPONSE command from the device.

    Command: MIC_RESPONSE (0x12)
    """
    logging.info(f"Mic response received from {side}")
    # Additional processing can be implemented here
    
async def handle_receive_mic_data(side: str, sender: str, data: bytes) -> asyncio.Future:
    """
    Handle the RECEIVE_MIC_DATA command from the device.

    Command: RECEIVE_MIC_DATA (0x13)
    """
    logging.info(f"Received mic data from {side}")
    # Additional processing can be implemented here
    
async def handle_init(side: str, sender: str, data: bytes) -> asyncio.Future:
    """
    Handle the INIT command from the device.

    Command: INIT (0x10)
    """
    logging.info(f"Init command received from {side}")
    # Additional processing can be implemented here
    
async def handle_send_result(side: str, sender: str, data: bytes) -> asyncio.Future:
    """
    Handle the SEND_RESULT command from the device.

    Command: SEND_RESULT (0x14)
    """
    logging.info(f"Result received from {side}")
    # Additional processing can be implemented here
    
async def handle_quick_note(side: str, sender: str, data: bytes) -> asyncio.Future:
    """
    Handle the QUICK_NOTE command from the device.

    Command: QUICK_NOTE (0x15)
    """
    logging.info(f"Quick note received from {side}")
    # Additional processing can be implemented here
    
async def handle_dashboard(side: str, sender: str, data: bytes) -> asyncio.Future:
    """
    Handle the DASHBOARD command from the device.

    Command: DASHBOARD (0x22)
    """
    logging.info(f"Dashboard command received from {side}")
    # Additional processing can be implemented here
    
async def handle_notification(side: str, sender: str, data: bytes) -> asyncio.Future:
    """
    Handle the NOTIFICATION command from the device.

    Command: NOTIFICATION (0x23)
    """
    logging.info(f"Notification received from {side}")
    # Additional processing can be implemented here
    
    

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the Redis channel
NOTIFICATION_CHANNEL = "notifications"

# Mapping of command bytes to handler functions
# Mapping of commands to handler functions
COMMAND_HANDLERS: Dict[int, Callable[[str, str, bytes], asyncio.Future]] = {
    Command.HEARTBEAT: handle_heartbeat,
    Command.START_AI: handle_start_ai,
    Command.OPEN_MIC: handle_open_mic,
    Command.MIC_RESPONSE: handle_mic_response,
    Command.RECEIVE_MIC_DATA: handle_receive_mic_data,
    Command.INIT: handle_init,
    Command.SEND_RESULT: handle_send_result,
    Command.QUICK_NOTE: handle_quick_note,
    Command.DASHBOARD: handle_dashboard,
    Command.NOTIFICATION: handle_notification,
    # Add other command handlers as necessary
}


class NotificationReceiver:
    def __init__(self, redis_url: str = "redis://localhost"):
        self.redis_url = redis_url
        self.redis_client = aioredis.from_url(self.redis_url, decode_responses=True)
        self.handlers = COMMAND_HANDLERS

    async def connect(self):
        """Initialize the Redis connection and subscribe to the notifications channel."""
        try:
            await self.redis_client.ping()
            logger.info("Connected to Redis server.")
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe(NOTIFICATION_CHANNEL)
            logger.info(f"Subscribed to Redis channel: {NOTIFICATION_CHANNEL}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis server: {e}")
            raise

    async def listen(self):
        """Listen for incoming notifications and dispatch them to handlers."""
        try:
            async for message in self.pubsub.listen():
                if message is None:
                    continue
                if message["type"] != "message":
                    continue

                data = message.get("data")
                if not data:
                    logger.warning("Received empty notification message.")
                    continue

                try:
                    notification = json.loads(data)
                    logger.info(f"Received notification: {notification}")
                except json.JSONDecodeError:
                    logger.error("Failed to decode JSON notification.")
                    continue

                # Dispatch the notification to the appropriate handler
                await self.dispatch_notification(notification)
        except asyncio.CancelledError:
            logger.info("Notification receiver has been cancelled.")
        except Exception as e:
            logger.error(f"Error while listening for notifications: {e}")
        finally:
            await self.pubsub.unsubscribe(NOTIFICATION_CHANNEL)
            await self.redis_client.close()
            logger.info("Redis connection closed.")

    async def dispatch_notification(self, notification: Dict[str, Any]):
        """Dispatch the notification to the appropriate handler based on its type."""
        side = notification.get("side")
        sender = notification.get("sender")
        data_hex = notification.get("data")

        if not all([side, sender, data_hex]):
            logger.warning("Incomplete notification received. 'side', 'sender', or 'data' missing.")
            return

        try:
            data_bytes = bytes.fromhex(data_hex)
        except ValueError:
            logger.error("Failed to convert data from hex to bytes.")
            return

        if not data_bytes:
            logger.warning("Notification data is empty after conversion.")
            return

        # Extract the command byte (assuming the first byte denotes the command)
        command_byte = data_bytes[0]
        try:
            command = Command(command_byte)
        except ValueError:
            logging.warning(
                f"Unknown command: 0x{command_byte:02X} received from {side}"
            )
            return
        
        handler = self.handlers.get(command)
        if not handler:
            logging.warning(
                f"No handler for command: {command.name} (0x{command_byte:02X}) received from {side}"
            )
            return

        logger.info(f"Dispatching command 0x{command_byte:02X} to handler '{handler.__name__}'")

        try:
            await handler(side, sender, data_bytes)
        except Exception as e:
            logger.error(f"Error handling command 0x{command_byte:02X}: {e}")

    async def run(self):
        """Run the notification receiver."""
        await self.connect()
        await self.listen()
        
if __name__ == "__main__":
    receiver = NotificationReceiver()
    asyncio.run(receiver.run())