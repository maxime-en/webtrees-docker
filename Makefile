# Makefile for building a Docker image using docker buildx

# Variables (override with `make IMAGE_NAME=myimage`)
IMAGE_NAME ?= webtrees
APP_VERSION ?= 2.2.1
CONTEXT ?= ./docker/

# Full image name
IMAGE_FULL_NAME := $(IMAGE_NAME):$(APP_VERSION)

.PHONY: all build push

all: build

# Download webtrees
download:
	curl -L -s -o docker/webtrees-$(APP_VERSION).zip \
		https://github.com/fisharebest/webtrees/releases/download/$(APP_VERSION)/webtrees-$(APP_VERSION).zip

# Build the Docker image
build: download
	docker buildx build \
		--tag $(IMAGE_FULL_NAME) \
		$(CONTEXT)
