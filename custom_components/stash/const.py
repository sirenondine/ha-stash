"""Constants for the Stash integration."""

DOMAIN = "stash"
DEFAULT_NAME = "Stash"
DEFAULT_PORT = 9999

# Configuration keys (stored in entry.data)
CONF_URL = "url"
CONF_API_KEY = "api_key"

# Options keys (stored in entry.options)
CONF_FAST_INTERVAL = "fast_interval"
CONF_SLOW_INTERVAL = "slow_interval"

# Default update intervals (seconds)
DEFAULT_FAST_INTERVAL = 30  # for job queue, DLNA, version
DEFAULT_SLOW_INTERVAL = 300  # for library stats

# Sensor types (library stats — polled slowly)
SENSOR_SCENE_COUNT = "scene_count"
SENSOR_PERFORMER_COUNT = "performer_count"
SENSOR_STUDIO_COUNT = "studio_count"
SENSOR_GROUP_COUNT = "group_count"
SENSOR_TAG_COUNT = "tag_count"
SENSOR_GALLERY_COUNT = "gallery_count"
SENSOR_IMAGE_COUNT = "image_count"
SENSOR_SCENES_SIZE = "scenes_size"
SENSOR_IMAGES_SIZE = "images_size"
SENSOR_SCENES_DURATION = "scenes_duration"
SENSOR_TOTAL_O_COUNT = "total_o_count"
SENSOR_TOTAL_PLAY_DURATION = "total_play_duration"
SENSOR_TOTAL_PLAY_COUNT = "total_play_count"
SENSOR_SCENES_PLAYED = "scenes_played"

# Sensor types (status — polled fast)
SENSOR_VERSION = "version"
SENSOR_ACTIVE_JOB = "active_job"

SENSOR_TYPES = {
    SENSOR_SCENE_COUNT: {
        "name": "Scenes",
        "icon": "mdi:filmstrip",
    },
    SENSOR_PERFORMER_COUNT: {
        "name": "Performers",
        "icon": "mdi:account-group",
    },
    SENSOR_STUDIO_COUNT: {
        "name": "Studios",
        "icon": "mdi:office-building",
    },
    SENSOR_GROUP_COUNT: {
        "name": "Groups",
        "icon": "mdi:movie-open",
    },
    SENSOR_TAG_COUNT: {
        "name": "Tags",
        "icon": "mdi:tag",
    },
    SENSOR_GALLERY_COUNT: {
        "name": "Galleries",
        "icon": "mdi:image-album",
    },
    SENSOR_IMAGE_COUNT: {
        "name": "Images",
        "icon": "mdi:image",
    },
    SENSOR_SCENES_SIZE: {
        "name": "Scenes Size",
        "icon": "mdi:database",
    },
    SENSOR_IMAGES_SIZE: {
        "name": "Images Size",
        "icon": "mdi:database",
    },
    SENSOR_SCENES_DURATION: {
        "name": "Scenes Duration",
        "icon": "mdi:clock-outline",
    },
    SENSOR_TOTAL_O_COUNT: {
        "name": "O Count",
        "icon": "mdi:water",
    },
    SENSOR_TOTAL_PLAY_DURATION: {
        "name": "Total Play Duration",
        "icon": "mdi:play-circle-outline",
    },
    SENSOR_TOTAL_PLAY_COUNT: {
        "name": "Total Play Count",
        "icon": "mdi:play",
    },
    SENSOR_SCENES_PLAYED: {
        "name": "Scenes Played",
        "icon": "mdi:filmstrip-box-multiple",
    },
}

# Binary sensor types
BINARY_SENSOR_ONLINE = "online"
BINARY_SENSOR_JOB_RUNNING = "job_running"
BINARY_SENSOR_UPDATE_AVAILABLE = "update_available"
BINARY_SENSOR_DLNA = "dlna"
BINARY_SENSOR_WEBSOCKET = "websocket"
