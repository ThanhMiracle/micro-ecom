pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
  }

  environment {
    DOCKER_BUILDKIT = "1"
    COMPOSE_DOCKER_CLI_BUILD = "1"
    COMPOSE_PROJECT_NAME = "microshop-ci-${env.BUILD_NUMBER}"
  }

  stages {

    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Preflight') {
      steps {
        sh '''#!/usr/bin/env bash
          set -euo pipefail
          echo "================ PRE-FLIGHT ================"
          echo "Node: $(hostname)"
          echo "User: $(id)"
          echo "Workspace: $PWD"
          echo "COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}"
          echo

          echo "== Docker Info =="
          docker version

          echo "== Docker Compose Info =="
          if docker compose version >/dev/null 2>&1; then
            docker compose version
            echo "Using docker compose v2"
          elif docker-compose version >/dev/null 2>&1; then
            docker-compose version
            echo "Using docker-compose v1"
          else
            echo "ERROR: docker compose not found"
            exit 1
          fi

          echo "== DNS sanity (host) =="
          getent hosts api.github.com || true
        '''
      }
    }

    stage('Build') {
      steps {
        sh '''#!/usr/bin/env bash
          set -euxo pipefail
          echo "================ BUILD ================"

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
        sh '''#!/usr/bin/env bash
          set -euxo pipefail
          echo "================ TEST ================"

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

          echo "== Current compose ps =="
          $C ps || true

          run_test () {
            svc="$1"
            echo
            echo "---------- RUN TEST: ${svc} ----------"

            mkdir -p ci-artifacts

            set +e
            $C run --rm "${svc}" 2>&1 | tee "ci-artifacts/${svc}.out.log"
            rc=${PIPESTATUS[0]}
            set -e

            echo "---------- RESULT: ${svc} exit=${rc} ----------"

            if [ "${rc}" -ne 0 ]; then
              echo
              echo "!!!!! TEST FAILED: ${svc} (exit=${rc}) !!!!!"
              echo "== Compose ps (on failure) =="
              $C ps || true

              echo "== Compose logs tail (on failure) =="
              $C logs --no-color --tail=300 || true

              cid=$($C ps -aq "${svc}" 2>/dev/null | head -n 1 || true)
              if [ -n "$cid" ]; then
                echo "== Docker logs for container $cid =="
                docker logs --tail 300 "$cid" || true
              fi

              exit "${rc}"
            fi
          }

          run_test auth-tests
          run_test product-tests
          run_test order-tests
          run_test payment-tests
          run_test notify-tests
        '''
      }
    }
  }

  post {
    always {
      sh '''#!/usr/bin/env bash
        set +e
        echo "================ POST / ALWAYS ================"

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

        echo "== Docker summary (host) =="
        docker ps -a > ci-artifacts/docker-ps-a.txt 2>&1 || true
        docker network ls > ci-artifacts/docker-networks.txt 2>&1 || true

        echo "== Cleaning up =="
        $C down -v --remove-orphans || true
      '''

      archiveArtifacts artifacts: 'ci-artifacts/*', allowEmptyArchive: true
      cleanWs()
    }
  }
}