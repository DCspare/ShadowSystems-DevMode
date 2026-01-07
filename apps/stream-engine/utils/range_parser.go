package utils

import (
	"fmt"
	"strconv"
	"strings"
)

// ParseRange matches the logic in your Python stream_routes.py.
// It takes the "bytes=0-1024" header and returns the start and end offsets.
func ParseRange(header string, size int64) (int64, int64, error) {
	if header == "" {
		return 0, size - 1, nil
	}

	parts := strings.Split(strings.TrimPrefix(header, "bytes="), "-")
	if len(parts) != 2 {
		return 0, 0, fmt.Errorf("invalid range format")
	}

	start, err := strconv.ParseInt(parts[0], 10, 64)
	if err != nil {
		start = 0
	}

	end, err := strconv.ParseInt(parts[1], 10, 64)
	if err != nil || end == 0 {
		end = size - 1
	}

	return start, end, nil
}