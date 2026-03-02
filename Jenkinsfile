pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
  }

  environment {
    DOCKER_BUILDKIT = "1"
    COMPOSE_DOCKER_CLI_BUILD = "1"
  }

  stages {

    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Preflight') {
      steps {
        sh '''
          set -euo pipefail

          echo "== Docker Info =="
          docker version

          if docker compose version >/dev/null 2>&1; then
            echo "Using docker compose v2"
          elif docker-compose version >/dev/null 2>&1; then
            echo "Using docker-compose v1"
          else
            echo "ERROR: docker compose not found"
            exit 1
          fi
        '''
      }
    }

    stage('Build') {
      steps {
        script {
          env.COMPOSE_PROJECT_NAME = "microshop-ci-${env.BUILD_NUMBER}"
        }

        sh '''
          set -euxo pipefail

          if docker compose version >/dev/null 2>&1; then
            COMPOSE="docker compose"
          else
            COMPOSE="docker-compose"
          fi

          C="$COMPOSE -p ${COMPOSE_PROJECT_NAME} -f docker-compose.yml -f docker-compose.ci.yml"

          echo "== Validating Compose Config =="
          $C config

          echo "== Pulling base images =="
          $C pull --ignore-pull-failures || true

          echo "== Building images =="
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

          C="$COMPOSE -p ${COMPOSE_PROJECT_NAME} -f docker-compose.yml -f docker-compose.ci.yml"

          echo "== Starting shared services =="
          $C up -d postgres rabbit mailhog

          echo "== Waiting for healthchecks (if supported) =="
          $C up -d --wait postgres rabbit mailhog || true

          echo "== Running test suites =="

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

        C="$COMPOSE -p ${COMPOSE_PROJECT_NAME} -f docker-compose.yml -f docker-compose.ci.yml"

        mkdir -p ci-artifacts

        echo "== Collecting logs =="
        $C ps > ci-artifacts/compose-ps.txt 2>&1 || true
        $C logs --no-color > ci-artifacts/compose-logs.txt 2>&1 || true
        $C config > ci-artifacts/compose-config.rendered.yml 2>&1 || true

        echo "== Cleaning up =="
        $C down -v --remove-orphans || true
      '''

      archiveArtifacts artifacts: 'ci-artifacts/*', allowEmptyArchive: true
      cleanWs()
    }
  }
}