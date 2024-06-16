# https://hub.docker.com/_/redis
FROM redis:7.2.4-alpine

# Add custom Redis configuration
COPY redis.conf /usr/local/etc/redis/redis.conf

# Use that config
CMD [ "redis-server", "/usr/local/etc/redis/redis.conf" ]
