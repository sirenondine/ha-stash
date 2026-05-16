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
SENSOR_MOVIE_COUNT = "movie_count"
SENSOR_TAG_COUNT = "tag_count"
SENSOR_GALLERY_COUNT = "gallery_count"
SENSOR_IMAGE_COUNT = "image_count"
SENSOR_TOTAL_SIZE = "total_size"
SENSOR_TOTAL_DURATION = "total_duration"

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
    SENSOR_MOVIE_COUNT: {
        "name": "Movies",
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
    SENSOR_TOTAL_SIZE: {
        "name": "Total Size",
        "icon": "mdi:database",
    },
    SENSOR_TOTAL_DURATION: {
        "name": "Total Duration",
        "icon": "mdi:clock-outline",
    },
}
