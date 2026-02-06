#!/bin/bash

services=("web" "auth" "product" "order" "notify")

for s in "${services[@]}"; do
  docker tag microshop_fullstack-$s:latest thanh2909/$s-service:v0.1
  docker push thanh2909/$s-service:v0.1
done