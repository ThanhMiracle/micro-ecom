pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
  }

  environment {
    COMPOSE_PROJECT_NAME = "microshop-ci-${env.BUILD_NUMBER}"
    DOCKER_BUILDKIT = "1"
    COMPOSE_DOCKER_CLI_BUILD = "1"
  }

  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

    stage('Preflight') {
      steps {
        sh '''
          set -euo pipefail
          docker version

          if docker compose version >/dev/null 2>&1; then
            echo "Using: docker compose"
          elif docker-compose version >/dev/null 2>&1; then
            echo "Using: docker-compose"
          else
            echo "ERROR: docker compose not found"
            exit 1
          fi
        '''
      }
    }

    stage('Build') {
      steps {
        sh '''
          set -euxo pipefail

          if docker compose version >/dev/null 2>&1; then
            COMPOSE="docker compose"
          else
            COMPOSE="docker-compose"
          fi

          C="$COMPOSE -p $COMPOSE_PROJECT_NAME -f docker-compose.yml -f docker-compose.ci.yml"

          $C version
          $C config >/dev/null

          $C pull --ignore-pull-failures
          $C build --pull
        '''
      }
    }

    stage('Test') {
      steps {
        sh '''
          set -euxo pipefail

          if docker compose version >/dev/null 2>&1; then
            COMPOSE="docker compose"
          else
            COMPOSE="docker-compose"
          fi

          C="$COMPOSE -p $COMPOSE_PROJECT_NAME -f docker-compose.yml -f docker-compose.ci.yml"

          # Start shared deps
          $C up -d postgres rabbit mailhog

          # If you have healthchecks, prefer waiting (compose v2)
          if $COMPOSE version | head -n1 | grep -q "Docker Compose version v"; then
            # best-effort: only works when healthchecks exist
            $C up -d --wait postgres rabbit mailhog || true
          fi

          # OPTIONAL: Start app services only if your tests need them running
          # $C up -d auth product order payment notify

          # Run tests
          $C run --rm auth-tests
          $C run --rm product-tests
          $C run --rm order-tests
          $C run --rm payment-tests
          $C run --rm notify-tests
        '''
      }
    }
  }

  post {
    always {
      sh '''
        set +e

        if docker compose version >/dev/null 2>&1; then
          COMPOSE="docker compose"
        else
          COMPOSE="docker-compose"
        fi

        C="$COMPOSE -p $COMPOSE_PROJECT_NAME -f docker-compose.yml -f docker-compose.ci.yml"

        mkdir -p ci-artifacts
        $C ps > ci-artifacts/compose-ps.txt 2>&1 || true
        $C logs --no-color > ci-artifacts/compose-logs.txt 2>&1 || true
        $C config > ci-artifacts/compose-config.rendered.yml 2>&1 || true

        $C down -v --remove-orphans || true
      '''
      archiveArtifacts artifacts: 'ci-artifacts/*', allowEmptyArchive: true
      cleanWs()
    }
  }
}