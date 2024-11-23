import json
import logging
import redis.asyncio as aioredis

from even_glasses.models import (
    SilentModeStatus,
    BrightnessAuto,
    GlassesWearStatus,
    DashboardPosition,
)
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the Redis channel
COMMAND_CHANNEL = "commands"

class CommandSender:
    def __init__(self, redis_url: str = "redis://localhost"):
        self.redis_url = redis_url
        self.redis_client = aioredis.from_url(self.redis_url, decode_responses=True)

    async def connect(self):
        """Initialize the Redis connection."""
        try:
            await self.redis_client.ping()
            logger.info("Connected to Redis server.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis server: {e}")
            raise

    async def send_command(self, command_name: str, args=None, kwargs=None):
        """Publish a command to the Redis COMMAND_CHANNEL."""
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}

        command_message = {
            "command": command_name,
            "args": args,
            "kwargs": kwargs
        }

        try:
            await self.redis_client.publish(COMMAND_CHANNEL, json.dumps(command_message))
            logger.info(f"Published command to Redis: {command_message}")
        except Exception as e:
            logger.error(f"Failed to publish command to Redis: {e}")

    async def send_text_command(self, text_message: str, duration: int = 5):
        """Send a text message to the glasses."""
        await self.send_command(
            command_name="send_text",
            args=[text_message],
            kwargs={"duration": duration}
        )

    async def send_notification_command(self, notification: Dict[str, Any]):
        """Send a notification to the glasses."""
        # Assuming notification dict matches NCSNotification structure
        await self.send_command(
            command_name="send_notification",
            args=[],
            kwargs={"notification": notification}
        )

    async def send_rsvp_command(self, text: str, config: Dict[str, Any]):
        """Send RSVP (Rapid Serial Visual Presentation) text to the glasses."""
        await self.send_command(
            command_name="send_rsvp",
            args=[text],
            kwargs={"config": config}
        )

    async def apply_silent_mode_command(self, status: str):
        """Apply silent mode to the glasses."""
        try:
            status_enum = SilentModeStatus[status]
        except KeyError:
            logger.error(f"Invalid silent mode status: {status}. Use 'ON' or 'OFF'.")
            return

        await self.send_command(
            command_name="apply_silent_mode",
            args=[],
            kwargs={"status": status_enum.value}
        )

    async def apply_brightness_command(self, level: int, auto: str):
        """Adjust the brightness of the glasses."""
        try:
            auto_enum = BrightnessAuto[auto.upper()]
        except KeyError:
            logger.error(f"Invalid brightness auto value: {auto}. Use 'ON' or 'OFF'.")
            return

        await self.send_command(
            command_name="apply_brightness",
            args=[],
            kwargs={"level": level, "auto": auto_enum.value}
        )

    async def apply_headup_angle_command(self, angle: int):
        """Adjust the head-up display angle."""
        await self.send_command(
            command_name="apply_headup_angle",
            args=[],
            kwargs={"angle": angle}
        )

    async def add_or_update_note_command(self, note_number: int, title: str, text: str):
        """Add or update a note on the glasses."""
        await self.send_command(
            command_name="add_or_update_note",
            args=[note_number],
            kwargs={"title": title, "text": text}
        )

    async def delete_note_command(self, note_number: int):
        """Delete a note from the glasses."""
        await self.send_command(
            command_name="delete_note",
            args=[note_number],
            kwargs={}
        )

    async def show_dashboard_command(self, position: int):
        """Show the dashboard on the glasses."""
        # Validate position using DashboardPosition enum
        if position not in DashboardPosition._value2member_map_:
            logger.error(f"Invalid dashboard position: {position}.")
            return

        await self.send_command(
            command_name="show_dashboard",
            args=[],
            kwargs={"position": position}
        )

    async def hide_dashboard_command(self, position: int):
        """Hide the dashboard from the glasses."""
        # Validate position using DashboardPosition enum
        if position not in DashboardPosition._value2member_map_:
            logger.error(f"Invalid dashboard position: {position}.")
            return

        await self.send_command(
            command_name="hide_dashboard",
            args=[],
            kwargs={"position": position}
        )

    async def apply_glasses_wear_command(self, status: str):
        """Apply glasses wear status."""
        try:
            status_enum = GlassesWearStatus[status.upper()]
        except KeyError:
            logger.error(f"Invalid glasses wear status: {status}. Use 'ON' or 'OFF'.")
            return

        await self.send_command(
            command_name="apply_glasses_wear",
            args=[],
            kwargs={"status": status_enum.value}
        )

    async def close(self):
        """Close the Redis connection."""
        try:
            await self.redis_client.close()
            logger.info("Closed Redis connection.")
        except Exception as e:
            logger.error(f"Failed to close Redis connection: {e}")


