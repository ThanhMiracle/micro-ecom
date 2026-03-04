# Command to delete redudant images
docker images --format "{{.Repository}}:{{.Tag}}" | grep microshop-ci- | grep -v microshop-ci-36- | xargs -r docker rmi
