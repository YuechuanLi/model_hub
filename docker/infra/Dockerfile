FROM postgres:16-alpine

# Install Redis
RUN apk add --no-cache redis

# Copy startup script
COPY start-all.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/start-all.sh

# Expose Redis port (Postgres 5432 is already exposed)
EXPOSE 6379

ENTRYPOINT ["start-all.sh"]
CMD ["postgres"]
