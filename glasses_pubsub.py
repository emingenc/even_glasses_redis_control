import json
import asyncio
import logging
import redis.asyncio as aioredis
from even_glasses.bluetooth_manager import GlassesManager
from even_glasses.commands import (
    send_text,
    send_rsvp,
    send_notification,
    apply_silent_mode,
    apply_brightness,
    apply_headup_angle,
    add_or_update_note,
    delete_note,
    show_dashboard,
    hide_dashboard,
    apply_glasses_wear,
)
from even_glasses.models import (
    RSVPConfig,
    SilentModeStatus,
    BrightnessAuto,
    GlassesWearStatus,
    DashboardPosition,
    NCSNotification,
)
from typing import Callable, Any, Dict
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the Redis channels
COMMAND_CHANNEL = "commands"
NOTIFICATION_CHANNEL = "notifications"

# Command mapping
COMMAND_MAPPING = {
    "send_text": send_text,
    "send_rsvp": send_rsvp,
    "send_notification": send_notification,
    "apply_silent_mode": apply_silent_mode,
    "apply_brightness": apply_brightness,
    "apply_headup_angle": apply_headup_angle,
    "add_or_update_note": add_or_update_note,
    "delete_note": delete_note,
    "show_dashboard": show_dashboard,
    "hide_dashboard": hide_dashboard,
    "apply_glasses_wear": apply_glasses_wear,
}

# Deserialization mapping
COMMAND_DESERIALIZERS: Dict[str, Dict[str, Callable[[Any], Any]]] = {
    "send_rsvp": {
        "config": RSVPConfig.parse_obj  # Pydantic model deserialization
    },
    "send_notification": {
        "notification": NCSNotification.parse_obj
    },
    "apply_silent_mode": {
        "status": SilentModeStatus  # Enum deserialization
    },
    "apply_brightness": {
        "auto": BrightnessAuto
    },
    "apply_glasses_wear": {
        "status": GlassesWearStatus
    },
    "show_dashboard": {
        "position": DashboardPosition
    },
    "hide_dashboard": {
        "position": DashboardPosition
    },
    # Add more commands and their deserializers here if needed
}

async def redis_listener(manager: GlassesManager, redis_url: str):
    """Listen to Redis commands and execute them."""
    redis_client = aioredis.from_url(redis_url, decode_responses=True)
    async with redis_client.pubsub() as pubsub:
        await pubsub.subscribe(COMMAND_CHANNEL)
        logger.info(f"Subscribed to Redis channel: {COMMAND_CHANNEL}")

        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                try:
                    data = message["data"]
                    logger.info(f"Received message from Redis: {data}")
                    await handle_command(manager, data)
                except Exception as e:
                    logger.error(f"Error handling Redis message: {e}")
            await asyncio.sleep(0.01)  # Slight delay to prevent tight loop

async def handle_command(manager: GlassesManager, message: str):
    """Parse and execute commands received from Redis."""
    try:
        # Expecting the message to be in JSON format
        command_data = json.loads(message)
        command_name = command_data.get("command")
        args = command_data.get("args", [])
        kwargs = command_data.get("kwargs", {})

        if command_name in COMMAND_MAPPING:
            command_func = COMMAND_MAPPING[command_name]
            
            # Get deserializers for the command
            deserializers = COMMAND_DESERIALIZERS.get(command_name, {})
            
            # Deserialize each parameter as needed
            for param, deserializer in deserializers.items():
                if param in kwargs:
                    raw_value = kwargs[param]
                    try:
                        if isinstance(deserializer, type) and issubclass(deserializer, Enum):
                            # Enum deserialization
                            kwargs[param] = deserializer(raw_value)
                        elif callable(deserializer):
                            # Pydantic model deserialization
                            kwargs[param] = deserializer(raw_value)
                        else:
                            # Fallback for any other type
                            kwargs[param] = deserializer(raw_value)
                    except Exception as e:
                        logger.error(f"Failed to deserialize parameter '{param}' for command '{command_name}': {e}")
                        return  # Skip executing the command if deserialization fails
            
            # Execute the command function with the deserialized arguments
            result = await command_func(manager, *args, **kwargs)
            logger.info(f"Executed command '{command_name}' with result: {result}")
        else:
            logger.warning(f"Unknown command received: {command_name}")
    except json.JSONDecodeError:
        logger.error("Failed to decode JSON message.")
    except Exception as e:
        logger.error(f"Exception in handle_command: {e}")

async def notification_publisher(manager: GlassesManager, redis_url: str):
    """Publish glasses notifications to Redis."""
    redis_client = aioredis.from_url(redis_url, decode_responses=True)
    notification_queue = asyncio.Queue()

    # Modify the notification handler to put notifications into a queue
    async def notification_handler(glass, sender, data):
        await notification_queue.put((glass, sender, data))

    # Assign the modified notification handler
    if manager.left_glass:
        manager.left_glass.notification_handler = notification_handler
    if manager.right_glass:
        manager.right_glass.notification_handler = notification_handler

    logger.info(f"Notification publisher started on Redis channel: {NOTIFICATION_CHANNEL}")

    while True:
        glass, sender, data = await notification_queue.get()
        # Process the notification data as needed
        # For simplicity, we'll just publish the raw data
        notification_message = {
            "side": glass.side,
            "sender": str(sender),
            "data": data.hex(),
        }
        await redis_client.publish(NOTIFICATION_CHANNEL, json.dumps(notification_message))
        logger.info(f"Published notification to Redis: {notification_message}")

async def main():
    redis_url = "redis://localhost"
    manager = GlassesManager(left_address=None, right_address=None)
    connected = await manager.scan_and_connect()

    if connected:
        logger.info("Connected to glasses.")

        # Send an initial message to the glasses
        await send_text(manager=manager, text_message="Hello, I am connected.")

        # Start the Redis listener and notification publisher
        listener_task = asyncio.create_task(redis_listener(manager, redis_url))
        publisher_task = asyncio.create_task(notification_publisher(manager, redis_url))

        # Run indefinitely
        try:
            await asyncio.gather(listener_task, publisher_task)
        except asyncio.CancelledError:
            logger.info("Tasks have been cancelled.")
        except KeyboardInterrupt:
            logger.info("Interrupted by user.")
        finally:
            listener_task.cancel()
            publisher_task.cancel()
            await manager.disconnect_all()
    else:
        logger.error("Failed to connect to glasses.")

if __name__ == "__main__":
    # Start the Redis server before running this script
    # docker run --name redis-server -p 6379:6379 -d redis
    asyncio.run(main())