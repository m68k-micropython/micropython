#!/bin/sh

tea login add --url "$FORGE_SERVER_URL"

tea release asset create "${TAG}" dist/*
