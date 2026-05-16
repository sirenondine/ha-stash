"""Constants for the Stash integration."""

DOMAIN = "stash"
DEFAULT_NAME = "Stash"
DEFAULT_PORT = 9999

# Configuration
CONF_URL = "url"
CONF_API_KEY = "api_key"

# Update interval
SCAN_INTERVAL = 300  # 5 minutes

# Sensor types
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
