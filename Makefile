.PHONY: build run test clean docker-build docker-run

APP_NAME := expert-commentary-service
BIN_DIR := bin
BIN := $(BIN_DIR)/$(APP_NAME)

build: $(BIN)

$(BIN): go.mod $(shell find . -name '*.go')
	@mkdir -p $(BIN_DIR)
	go build -ldflags="-s -w" -o $(BIN) ./cmd/server

run: build
	./$(BIN)

test:
	go test ./... -v -count=1

clean:
	rm -rf $(BIN_DIR)

docker-build:
	docker build -t $(APP_NAME):latest .

docker-run: docker-build
	docker run --rm -p 8080:8080 $(APP_NAME):latest

# Quick smoke test against a running instance
smoke:
	curl -s -X POST http://localhost:8080/api/v1/generate-commentary \
	  -H 'Content-Type: application/json' \
	  -d '{"event_id":1,"program_name":"Clinical Chemistry","program_type":"quantitative","summary":{"total_participants":150,"satisfactory":130,"questionable":12,"unsatisfactory":8},"analytes":[{"name":"Glucose","consensus_mean":5.2,"consensus_sd":0.15,"unit":"mmol/L","sdpa":0.5,"outlier_count":3,"z_score_range":[-4.1,3.8],"grade_counts":{"satisfactory":140,"questionable":7,"unsatisfactory":3}},{"name":"Sodium","consensus_mean":140,"consensus_sd":2.1,"unit":"mmol/L","sdpa":1.5,"outlier_count":1,"z_score_range":[-2.8,2.1],"grade_counts":{"satisfactory":145,"questionable":4,"unsatisfactory":1}}]}' | jq .
