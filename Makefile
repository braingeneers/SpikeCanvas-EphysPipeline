.DEFAULT_GOAL := help

TAG ?=

.PHONY: help require-tag ephys-build ephys-push listener-build listener-push dashboard-build dashboard-push release-build release-push release-all

help:
	@printf '%s\n' \
		'Available targets:' \
		'  make ephys-build TAG=vX.YY' \
		'  make ephys-push TAG=vX.YY' \
		'  make listener-build TAG=vX.YY' \
		'  make listener-push TAG=vX.YY' \
		'  make dashboard-build TAG=vX.YY' \
		'  make dashboard-push TAG=vX.YY' \
		'  make release-build TAG=vX.YY' \
		'  make release-push TAG=vX.YY' \
		'  make release-all TAG=vX.YY'

require-tag:
	@if [ -z "$(TAG)" ]; then \
		echo 'Error: TAG is required. Example: make release-all TAG=v0.77' >&2; \
		exit 1; \
	fi

ephys-build: require-tag
	TAG="$(TAG)" ./Algorithms/ephys_pipeline/sh/build.sh

ephys-push: require-tag
	TAG="$(TAG)" ./Algorithms/ephys_pipeline/sh/push.sh

listener-build: require-tag
	TAG="$(TAG)" ./Services/Spike_Sorting_Listener/sh/build.sh

listener-push: require-tag
	TAG="$(TAG)" ./Services/Spike_Sorting_Listener/sh/push.sh

dashboard-build: require-tag
	TAG="$(TAG)" ./Services/MaxWell_Dashboard/sh/build.sh

dashboard-push: require-tag
	TAG="$(TAG)" ./Services/MaxWell_Dashboard/sh/push.sh

release-build: ephys-build listener-build dashboard-build

release-push: ephys-push listener-push dashboard-push

release-all: release-build release-push
