# STAGE 1: The Build Room
FROM golang:1.22-alpine AS builder

WORKDIR /app
COPY go.mod ./
RUN go mod download

COPY . .
# Compile for Performance (stripped of debug info)
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o stream-engine .

# STAGE 2: The Action Room (Production Image)
FROM alpine:latest
RUN apk add --no-cache ca-certificates ffmpeg

WORKDIR /root/
COPY --from=builder /app/stream-engine .

EXPOSE 8000
CMD ["./stream-engine"]
