# apps/stream-engine/Dockerfile

# STAGE 1: The Build Room
FROM golang:1.24-alpine AS builder

WORKDIR /app

# 1. Install Git (Required for some 'go get' operations)
RUN apk add --no-cache git

# 2. Dependency Caching layer (Copy mod AND sum)
COPY go.mod go.sum ./
RUN go mod download

# 3. Compilation
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o stream-engine .

# STAGE 2: The Action Room (Production Image)
FROM alpine:latest

# 1. Runtime Deps
RUN apk add --no-cache ca-certificates ffmpeg mailcap

WORKDIR /app

# 2. Copy Binary
COPY --from=builder /app/stream-engine .

# 3. Secure Permissions (User 1000)
# Matches your other containers
RUN adduser -D -u 1000 user \
    && chown -R 1000:1000 /app

USER 1000
EXPOSE 8000

CMD ["./stream-engine"]
